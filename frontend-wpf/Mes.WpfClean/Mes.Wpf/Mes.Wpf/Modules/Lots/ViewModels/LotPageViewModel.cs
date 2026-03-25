using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Lots.Dtos;

namespace Mes.Wpf.Modules.Lots.ViewModels
{
    public class LotPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private LotListItemDto? _selectedItem;
        private LotDetailDto? _selectedDetail;
        private int _currentPage = 1;
        private int _pageSize = 10;
        private int _totalCount;

        public LotPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            SearchModel = new LotProcessSearchModel();

            Items = new ObservableCollection<LotListItemDto>();
            Steps = new ObservableCollection<LotStepDto>();

            StatusOptions = new ObservableCollection<string>
            {
                "전체",
                "WAITING",
                "IN_PROGRESS",
                "DONE"
            };

            SearchCommand = new AsyncRelayCommand(SearchAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
            PrevPageCommand = new AsyncRelayCommand(GoPreviousPageAsync, () => !IsLoading && HasPreviousPage);
            NextPageCommand = new AsyncRelayCommand(GoNextPageAsync, () => !IsLoading && HasNextPage);

            StartStepCommand = new AsyncRelayCommand<LotStepDto>(
                StartStepAsync,
                step => !IsLoading && step != null && step.CanStart);

            CompleteStepCommand = new AsyncRelayCommand<LotStepDto>(
                CompleteStepAsync,
                step => !IsLoading && step != null && step.CanComplete);
        }

        public LotProcessSearchModel SearchModel { get; }

        public ObservableCollection<LotListItemDto> Items { get; }

        public ObservableCollection<LotStepDto> Steps { get; }

        public ObservableCollection<string> StatusOptions { get; }

        public ICommand SearchCommand { get; }

        public ICommand ResetCommand { get; }

        public ICommand PrevPageCommand { get; }

        public ICommand NextPageCommand { get; }

        public ICommand StartStepCommand { get; }

        public ICommand CompleteStepCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (SetProperty(ref _isLoading, value))
                {
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public LotListItemDto? SelectedItem
        {
            get => _selectedItem;
            set
            {
                if (SetProperty(ref _selectedItem, value))
                {
                    _ = OnSelectedItemChangedAsync(value);
                }
            }
        }

        public LotDetailDto? SelectedDetail
        {
            get => _selectedDetail;
            set => SetProperty(ref _selectedDetail, value);
        }

        public int CurrentPage
        {
            get => _currentPage;
            set
            {
                if (SetProperty(ref _currentPage, value))
                {
                    OnPropertyChanged(nameof(TotalPages));
                    OnPropertyChanged(nameof(HasPreviousPage));
                    OnPropertyChanged(nameof(HasNextPage));
                    OnPropertyChanged(nameof(PageDisplayText));
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public int PageSize
        {
            get => _pageSize;
            set
            {
                if (SetProperty(ref _pageSize, value))
                {
                    OnPropertyChanged(nameof(TotalPages));
                    OnPropertyChanged(nameof(HasPreviousPage));
                    OnPropertyChanged(nameof(HasNextPage));
                    OnPropertyChanged(nameof(PageDisplayText));
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public int TotalCount
        {
            get => _totalCount;
            set
            {
                if (SetProperty(ref _totalCount, value))
                {
                    OnPropertyChanged(nameof(TotalPages));
                    OnPropertyChanged(nameof(HasPreviousPage));
                    OnPropertyChanged(nameof(HasNextPage));
                    OnPropertyChanged(nameof(PageDisplayText));
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public int TotalPages
        {
            get
            {
                if (PageSize <= 0)
                {
                    return 1;
                }

                return Math.Max(1, (int)Math.Ceiling((double)TotalCount / PageSize));
            }
        }

        public bool HasPreviousPage => CurrentPage > 1;

        public bool HasNextPage => CurrentPage < TotalPages;

        public string PageDisplayText => $"{CurrentPage} / {TotalPages}  (총 {TotalCount:N0}건)";

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        public async Task SearchAsync()
        {
            CurrentPage = 1;
            await SearchInternalAsync(keepSelection: false);
        }

        public async Task ResetAsync()
        {
            SearchModel.Clear();
            CurrentPage = 1;
            await SearchInternalAsync(keepSelection: false);
        }

        public async Task LoadLotDetailAsync(long lotId)
        {
            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<LotDetailDto>($"{ApiRoutes.Lots}/{lotId}");
                if (!result.Success || result.Data == null)
                {
                    SelectedDetail = null;
                    Steps.Clear();
                    _messageService.ShowError(result.Message ?? "LOT 상세 조회에 실패했습니다.");
                    return;
                }

                SelectedDetail = result.Data;

                Steps.Clear();
                foreach (var step in result.Data.Steps.OrderBy(x => x.StepSeq))
                {
                    Steps.Add(step);
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        public async Task StartStepAsync(LotStepDto? step)
        {
            if (step == null || SelectedItem == null)
            {
                return;
            }

            var confirm = _messageService.Confirm($"[{step.ProcessName}] 공정을 시작하시겠습니까?");
            if (!confirm)
            {
                return;
            }

            try
            {
                IsLoading = true;

                var result = await _apiClient.PostAsync<object, object>(
                    $"{ApiRoutes.LotSteps}/{step.LotStepId}/start",
                    new { });

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "공정 시작 처리에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("공정 시작 처리되었습니다.");
            }
            finally
            {
                IsLoading = false;
            }

            await RefreshCurrentSelectionAsync();
            await SearchAsyncKeepSelectionAsync();
        }

        public async Task CompleteStepAsync(LotStepDto? step)
        {
            if (step == null || SelectedItem == null)
            {
                return;
            }

            var confirm = _messageService.Confirm($"[{step.ProcessName}] 공정을 완료하시겠습니까?");
            if (!confirm)
            {
                return;
            }

            try
            {
                IsLoading = true;

                var result = await _apiClient.PostAsync<object, object>(
                    $"{ApiRoutes.LotSteps}/{step.LotStepId}/complete",
                    new { });

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "공정 완료 처리에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("공정 완료 처리되었습니다.");
            }
            finally
            {
                IsLoading = false;
            }

            await RefreshCurrentSelectionAsync();
            await SearchAsyncKeepSelectionAsync();
        }

        public async Task GoPreviousPageAsync()
        {
            if (!HasPreviousPage)
            {
                return;
            }

            CurrentPage--;
            await SearchInternalAsync(keepSelection: false);
        }

        public async Task GoNextPageAsync()
        {
            if (!HasNextPage)
            {
                return;
            }

            CurrentPage++;
            await SearchInternalAsync(keepSelection: false);
        }

        private async Task OnSelectedItemChangedAsync(LotListItemDto? item)
        {
            if (item == null)
            {
                SelectedDetail = null;
                Steps.Clear();
                return;
            }

            await LoadLotDetailAsync(item.LotId);
        }

        private async Task RefreshCurrentSelectionAsync()
        {
            if (SelectedItem == null)
            {
                return;
            }

            await LoadLotDetailAsync(SelectedItem.LotId);
        }

        private async Task SearchAsyncKeepSelectionAsync()
        {
            await SearchInternalAsync(keepSelection: true);
        }

        private async Task SearchInternalAsync(bool keepSelection)
        {
            var currentLotId = keepSelection ? SelectedItem?.LotId : null;

            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<LotListResponseDto>(BuildSearchUrl());
                if (!result.Success || result.Data == null)
                {
                    Items.Clear();
                    Steps.Clear();
                    SelectedItem = null;
                    SelectedDetail = null;
                    TotalCount = 0;

                    _messageService.ShowError(result.Message ?? "LOT 목록 조회에 실패했습니다.");
                    return;
                }

                Items.Clear();
                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }

                CurrentPage = result.Data.Meta?.Page ?? CurrentPage;
                PageSize = result.Data.Meta?.Size ?? PageSize;
                TotalCount = result.Data.Meta?.Total ?? Items.Count;

                if (Items.Count == 0)
                {
                    SelectedItem = null;
                    SelectedDetail = null;
                    Steps.Clear();
                    return;
                }

                if (currentLotId.HasValue)
                {
                    SelectedItem = Items.FirstOrDefault(x => x.LotId == currentLotId.Value);
                }
                else
                {
                    SelectedItem = null;
                    SelectedDetail = null;
                    Steps.Clear();
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildSearchUrl()
        {
            var queryParts = new List<string>
            {
                $"page={CurrentPage}",
                $"size={PageSize}"
            };

            var keyword = SearchModel.Keyword?.Trim();
            if (!string.IsNullOrWhiteSpace(keyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(keyword)}");
            }

            if (!string.IsNullOrWhiteSpace(SearchModel.SelectedStatus) &&
                SearchModel.SelectedStatus != "전체")
            {
                queryParts.Add($"status={Uri.EscapeDataString(SearchModel.SelectedStatus)}");
            }

            return $"{ApiRoutes.Lots}?{string.Join("&", queryParts)}";
        }

        private void RaiseCommandCanExecuteChanged()
        {
            if (SearchCommand is AsyncRelayCommand searchCommand)
            {
                searchCommand.RaiseCanExecuteChanged();
            }

            if (ResetCommand is AsyncRelayCommand resetCommand)
            {
                resetCommand.RaiseCanExecuteChanged();
            }

            if (PrevPageCommand is AsyncRelayCommand prevPageCommand)
            {
                prevPageCommand.RaiseCanExecuteChanged();
            }

            if (NextPageCommand is AsyncRelayCommand nextPageCommand)
            {
                nextPageCommand.RaiseCanExecuteChanged();
            }

            if (StartStepCommand is AsyncRelayCommand<LotStepDto> startStepCommand)
            {
                startStepCommand.RaiseCanExecuteChanged();
            }

            if (CompleteStepCommand is AsyncRelayCommand<LotStepDto> completeStepCommand)
            {
                completeStepCommand.RaiseCanExecuteChanged();
            }
        }
    }

    public class AsyncRelayCommand : ICommand
    {
        private readonly Func<Task> _execute;
        private readonly Func<bool>? _canExecute;

        public AsyncRelayCommand(Func<Task> execute, Func<bool>? canExecute = null)
        {
            _execute = execute;
            _canExecute = canExecute;
        }

        public event EventHandler? CanExecuteChanged;

        public bool CanExecute(object? parameter)
        {
            return _canExecute?.Invoke() ?? true;
        }

        public async void Execute(object? parameter)
        {
            await _execute();
        }

        public void RaiseCanExecuteChanged()
        {
            CanExecuteChanged?.Invoke(this, EventArgs.Empty);
        }
    }

    public class AsyncRelayCommand<T> : ICommand
    {
        private readonly Func<T?, Task> _execute;
        private readonly Predicate<T?>? _canExecute;

        public AsyncRelayCommand(Func<T?, Task> execute, Predicate<T?>? canExecute = null)
        {
            _execute = execute;
            _canExecute = canExecute;
        }

        public event EventHandler? CanExecuteChanged;

        public bool CanExecute(object? parameter)
        {
            if (parameter == null)
            {
                return _canExecute == null || _canExecute(default);
            }

            if (parameter is T typedParameter)
            {
                return _canExecute?.Invoke(typedParameter) ?? true;
            }

            return false;
        }

        public async void Execute(object? parameter)
        {
            if (parameter == null)
            {
                await _execute(default);
                return;
            }

            if (parameter is T typedParameter)
            {
                await _execute(typedParameter);
            }
        }

        public void RaiseCanExecuteChanged()
        {
            CanExecuteChanged?.Invoke(this, EventArgs.Empty);
        }
    }
}