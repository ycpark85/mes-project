using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
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

        public LotPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            SearchModel = new LotProcessSearchModel();
            Items = new ObservableCollection<LotListItemDto>();
            Steps = new ObservableCollection<LotStepDto>();

            SearchCommand = new AsyncRelayCommand(SearchAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
            StartStepCommand = new AsyncRelayCommand<LotStepDto>(StartStepAsync, step => !IsLoading && step != null && step.CanStart);
            CompleteStepCommand = new AsyncRelayCommand<LotStepDto>(CompleteStepAsync, step => !IsLoading && step != null && step.CanComplete);
        }

        public LotProcessSearchModel SearchModel { get; }

        public ObservableCollection<LotListItemDto> Items { get; }

        public ObservableCollection<LotStepDto> Steps { get; }

        public ICommand SearchCommand { get; }

        public ICommand ResetCommand { get; }

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

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        public async Task SearchAsync()
        {
            try
            {
                IsLoading = true;

                var url = BuildSearchUrl();
                var result = await _apiClient.GetAsync<LotListResponseDto>(url);

                if (!result.Success || result.Data == null)
                {
                    Items.Clear();
                    Steps.Clear();
                    SelectedItem = null;
                    SelectedDetail = null;
                    _messageService.ShowError(result.Message ?? "LOT 목록 조회에 실패했습니다.");
                    return;
                }

                Items.Clear();
                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }

                SelectedDetail = null;
                Steps.Clear();

                if (Items.Count > 0)
                {
                    SelectedItem = Items.First();
                }
                else
                {
                    SelectedItem = null;
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        public async Task ResetAsync()
        {
            SearchModel.Clear();
            await SearchAsync();
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
            var currentLotId = SelectedItem?.LotId;

            try
            {
                IsLoading = true;

                var url = BuildSearchUrl();
                var result = await _apiClient.GetAsync<LotListResponseDto>(url);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "LOT 목록 재조회에 실패했습니다.");
                    return;
                }

                Items.Clear();
                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }

                if (currentLotId.HasValue)
                {
                    SelectedItem = Items.FirstOrDefault(x => x.LotId == currentLotId.Value) ?? Items.FirstOrDefault();
                }
                else
                {
                    SelectedItem = Items.FirstOrDefault();
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildSearchUrl()
        {
            var sb = new StringBuilder(ApiRoutes.Lots);
            var hasQuery = false;

            void AddQuery(string name, string? value)
            {
                if (string.IsNullOrWhiteSpace(value))
                {
                    return;
                }

                sb.Append(hasQuery ? "&" : "?");
                sb.Append(name);
                sb.Append("=");
                sb.Append(Uri.EscapeDataString(value));
                hasQuery = true;
            }

            AddQuery("created_date_from", SearchModel.CreatedDateFrom?.ToString("yyyy-MM-dd"));
            AddQuery("created_date_to", SearchModel.CreatedDateTo?.ToString("yyyy-MM-dd"));
            AddQuery("due_date_from", SearchModel.DueDateFrom?.ToString("yyyy-MM-dd"));
            AddQuery("due_date_to", SearchModel.DueDateTo?.ToString("yyyy-MM-dd"));

            var keyword = SearchModel.Keyword?.Trim();
            if (!string.IsNullOrWhiteSpace(keyword))
            {
                AddQuery("q", keyword);
            }

            return sb.ToString();
        }

        private void RaiseCommandCanExecuteChanged()
        {
            if (SearchCommand is AsyncRelayCommand search)
            {
                search.RaiseCanExecuteChanged();
            }

            if (ResetCommand is AsyncRelayCommand reset)
            {
                reset.RaiseCanExecuteChanged();
            }

            if (StartStepCommand is AsyncRelayCommand<LotStepDto> start)
            {
                start.RaiseCanExecuteChanged();
            }

            if (CompleteStepCommand is AsyncRelayCommand<LotStepDto> complete)
            {
                complete.RaiseCanExecuteChanged();
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

        public bool CanExecute(object? parameter) => _canExecute?.Invoke() ?? true;

        public async void Execute(object? parameter) => await _execute();

        public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
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
            if (parameter == null && typeof(T).IsValueType)
            {
                return _canExecute == null;
            }

            return _canExecute?.Invoke((T?)parameter) ?? true;
        }

        public async void Execute(object? parameter)
        {
            await _execute((T?)parameter);
        }

        public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
    }
}