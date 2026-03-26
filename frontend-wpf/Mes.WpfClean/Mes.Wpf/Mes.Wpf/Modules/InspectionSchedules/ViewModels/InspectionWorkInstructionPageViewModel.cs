using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;

namespace Mes.Wpf.Modules.InspectionSchedules.ViewModels
{
    public class InspectionWorkInstructionPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private InspectionWorkInstructionLotListItemDto? _selectedItem;
        private int _totalCount;

        public InspectionWorkInstructionPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<InspectionWorkInstructionLotListItemDto>();
            EditModel = new InspectionWorkInstructionEditModel();

            RefreshCommand = new AsyncRelayCommand(LoadAsync, () => !IsLoading);
            RegisterCommand = new AsyncRelayCommand(RegisterAsync, () => !IsLoading);
            ClearSelectionCommand = new AsyncRelayCommand(ClearSelectionAsync, () => !IsLoading);
            SelectLotCommand = new AsyncRelayCommand<InspectionWorkInstructionLotListItemDto>(SelectLotAsync, item => !IsLoading && item != null);

            EditModel.Clear();
        }

        public ObservableCollection<InspectionWorkInstructionLotListItemDto> Items { get; }

        public InspectionWorkInstructionEditModel EditModel { get; }

        public ICommand RefreshCommand { get; }
        public ICommand RegisterCommand { get; }
        public ICommand ClearSelectionCommand { get; }
        public ICommand SelectLotCommand { get; }

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

        public int TotalCount
        {
            get => _totalCount;
            set => SetProperty(ref _totalCount, value);
        }

        public InspectionWorkInstructionLotListItemDto? SelectedItem
        {
            get => _selectedItem;
            set
            {
                if (SetProperty(ref _selectedItem, value) && value != null)
                {
                    EditModel.LoadFromDto(value);
                }
            }
        }

        public async Task InitializeAsync()
        {
            await LoadAsync();
        }

        public async Task LoadAsync()
        {
            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<InspectionWorkInstructionLotListResponseDto>(BuildListUrl());
                if (!result.Success || result.Data == null)
                {
                    Items.Clear();
                    TotalCount = 0;
                    SelectedItem = null;
                    EditModel.Clear();
                    _messageService.ShowError(result.Message ?? "미등록 LOT 목록 조회에 실패했습니다.");
                    return;
                }

                Items.Clear();
                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }

                TotalCount = Items.Count;

                SelectedItem = null;
                EditModel.Clear();
            }
            finally
            {
                IsLoading = false;
            }
        }

        public Task SelectLotAsync(InspectionWorkInstructionLotListItemDto? item)
        {
            if (item == null)
            {
                return Task.CompletedTask;
            }

            SelectedItem = item;
            return Task.CompletedTask;
        }

        public Task ClearSelectionAsync()
        {
            SelectedItem = null;
            EditModel.Clear();
            return Task.CompletedTask;
        }

        public async Task RegisterAsync()
        {
            NormalizeEditModel();

            if (!ValidateForSave())
            {
                return;
            }

            var confirm = _messageService.Confirm($"LOT [{EditModel.LotNo}]의 검수 작업지시를 등록하시겠습니까?");
            if (!confirm)
            {
                return;
            }

            try
            {
                IsLoading = true;

                var request = new InspectionScheduleCreateRequest
                {
                    LotId = EditModel.LotId!.Value,
                    InspectionDate = EditModel.InspectionDate!.Value.Date,
                    Memo = string.IsNullOrWhiteSpace(EditModel.Memo) ? null : EditModel.Memo.Trim()
                };

                var result = await _apiClient.PostAsync<InspectionScheduleCreateRequest, object>(
                    ApiRoutes.InspectionSchedules,
                    request);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "검수 작업지시 등록에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("검수 작업지시가 등록되었습니다.");

                SelectedItem = null;
                EditModel.Clear();

                await LoadAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string>
            {
                "page=1",
                "size=200",
                "inspection_schedule_registered=false"
            };

            return $"{ApiRoutes.Lots}?{string.Join("&", queryParts)}";
        }

        private void NormalizeEditModel()
        {
            EditModel.LotNo = EditModel.LotNo?.Trim() ?? string.Empty;
            EditModel.ProductCode = EditModel.ProductCode?.Trim().ToUpperInvariant() ?? string.Empty;
            EditModel.ProductName = EditModel.ProductName?.Trim() ?? string.Empty;
            EditModel.PartnerName = EditModel.PartnerName?.Trim() ?? string.Empty;
            EditModel.Memo = EditModel.Memo?.Trim() ?? string.Empty;
        }

        private bool ValidateForSave()
        {
            if (!EditModel.LotId.HasValue)
            {
                _messageService.ShowWarning("등록할 LOT를 선택해주세요.");
                return false;
            }

            if (!EditModel.InspectionDate.HasValue)
            {
                _messageService.ShowWarning("검수일을 입력해주세요.");
                return false;
            }

            return true;
        }

        private void RaiseCommandCanExecuteChanged()
        {
            if (RefreshCommand is AsyncRelayCommand refreshCommand)
            {
                refreshCommand.RaiseCanExecuteChanged();
            }

            if (RegisterCommand is AsyncRelayCommand registerCommand)
            {
                registerCommand.RaiseCanExecuteChanged();
            }

            if (ClearSelectionCommand is AsyncRelayCommand clearSelectionCommand)
            {
                clearSelectionCommand.RaiseCanExecuteChanged();
            }

            if (SelectLotCommand is AsyncRelayCommand<InspectionWorkInstructionLotListItemDto> selectLotCommand)
            {
                selectLotCommand.RaiseCanExecuteChanged();
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