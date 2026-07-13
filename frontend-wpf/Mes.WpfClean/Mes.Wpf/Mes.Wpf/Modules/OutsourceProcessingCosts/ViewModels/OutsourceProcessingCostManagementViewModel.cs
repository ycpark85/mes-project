using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Threading.Tasks;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceProcessingCosts.Dtos;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.ViewModels
{
    public class OutsourceProcessingCostManagementViewModel : ViewModelBase
    {
        private const string CloseAction = "close";
        private const string ReopenAction = "reopen";
        private const string CancelAction = "cancel";
        private const int MinimumBundleTargetCount = 2;

        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private DateTime? _settlementMonth;
        private bool _useSettlementMonth = true;
        private DateTime? _dateFrom;
        private DateTime? _dateTo;
        private string _selectedProcessType = OutsourceProcessingCostDisplayOptions.CutProcessTypeCode;
        private string _selectedStatusCode = OutsourceProcessingCostDisplayOptions.AllStatusCode;
        private string _searchKeyword = string.Empty;
        private OutsourceProcessingCostTargetRowModel? _selectedTarget;
        private OutsourceProcessingCostGroupRowModel? _selectedCostGroup;
        private decimal? _standardAmount;
        private string _standardMemo = string.Empty;
        private decimal? _actualAmount;
        private DateTime? _actualBillingMonth;
        private string _actualMemo = string.Empty;
        private string _remark = string.Empty;
        private int _totalCount;
        private decimal _standardTotal;
        private decimal _actualTotal;
        private decimal _differenceTotal;
        private int _unclosedCount;
        private int _checkedTargetCount;

        public OutsourceProcessingCostManagementViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            ProcessTypeOptions = new ObservableCollection<CodeNameOption>(OutsourceProcessingCostDisplayOptions.ProcessTypes);
            StatusOptions = new ObservableCollection<CodeNameOption>(OutsourceProcessingCostDisplayOptions.Statuses);
            Targets = new ObservableCollection<OutsourceProcessingCostTargetRowModel>();
            CostGroups = new ObservableCollection<OutsourceProcessingCostGroupRowModel>();
            Allocations = new ObservableCollection<OutsourceProcessingCostAllocationRowModel>();

            SearchCommand = new AsyncRelayCommand(SearchAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
            CreateGroupCommand = new AsyncRelayCommand(CreateGroupAsync, () => !IsLoading && CanCreateBundle);
            SaveCostCommand = new AsyncRelayCommand(SaveCostAsync, () => !IsLoading && SelectedTarget != null);
            CloseCommand = new AsyncRelayCommand(CloseAsync, () => !IsLoading && SelectedCostGroup != null);
            ReopenCommand = new AsyncRelayCommand(ReopenAsync, () => !IsLoading && SelectedCostGroup != null);
            CancelCommand = new AsyncRelayCommand(CancelAsync, () => !IsLoading && SelectedCostGroup != null);
        }

        public ObservableCollection<CodeNameOption> ProcessTypeOptions { get; }
        public ObservableCollection<CodeNameOption> StatusOptions { get; }
        public ObservableCollection<OutsourceProcessingCostTargetRowModel> Targets { get; }
        public ObservableCollection<OutsourceProcessingCostGroupRowModel> CostGroups { get; }
        public ObservableCollection<OutsourceProcessingCostAllocationRowModel> Allocations { get; }

        public AsyncRelayCommand SearchCommand { get; }
        public AsyncRelayCommand ResetCommand { get; }
        public AsyncRelayCommand CreateGroupCommand { get; }
        public AsyncRelayCommand SaveCostCommand { get; }
        public AsyncRelayCommand CloseCommand { get; }
        public AsyncRelayCommand ReopenCommand { get; }
        public AsyncRelayCommand CancelCommand { get; }

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

        public DateTime? SettlementMonth
        {
            get => _settlementMonth;
            set => SetProperty(ref _settlementMonth, NormalizeMonth(value));
        }

        public bool UseSettlementMonth
        {
            get => _useSettlementMonth;
            set => SetProperty(ref _useSettlementMonth, value);
        }

        public DateTime? DateFrom
        {
            get => _dateFrom;
            set => SetProperty(ref _dateFrom, value);
        }

        public DateTime? DateTo
        {
            get => _dateTo;
            set => SetProperty(ref _dateTo, value);
        }

        public string SelectedProcessType
        {
            get => _selectedProcessType;
            set
            {
                if (SetProperty(ref _selectedProcessType, value))
                {
                    SelectedTarget = null;
                    Targets.Clear();
                }
            }
        }

        public string SelectedStatusCode
        {
            get => _selectedStatusCode;
            set => SetProperty(ref _selectedStatusCode, value);
        }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public OutsourceProcessingCostTargetRowModel? SelectedTarget
        {
            get => _selectedTarget;
            set
            {
                if (SetProperty(ref _selectedTarget, value))
                {
                    LoadSelectedTarget(value);
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public OutsourceProcessingCostGroupRowModel? SelectedCostGroup
        {
            get => _selectedCostGroup;
            set
            {
                if (SetProperty(ref _selectedCostGroup, value))
                {
                    LoadSelectedCostGroup(value);
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public decimal? StandardAmount
        {
            get => _standardAmount;
            set => SetProperty(ref _standardAmount, value);
        }

        public string StandardMemo
        {
            get => _standardMemo;
            set => SetProperty(ref _standardMemo, value ?? string.Empty);
        }

        public decimal? ActualAmount
        {
            get => _actualAmount;
            set => SetProperty(ref _actualAmount, value);
        }

        public DateTime? ActualBillingMonth
        {
            get => _actualBillingMonth;
            set => SetProperty(ref _actualBillingMonth, NormalizeMonth(value));
        }

        public string ActualMemo
        {
            get => _actualMemo;
            set => SetProperty(ref _actualMemo, value ?? string.Empty);
        }

        public string Remark
        {
            get => _remark;
            set => SetProperty(ref _remark, value ?? string.Empty);
        }

        public int TotalCount
        {
            get => _totalCount;
            set => SetProperty(ref _totalCount, value);
        }

        public decimal StandardTotal
        {
            get => _standardTotal;
            set => SetProperty(ref _standardTotal, value);
        }

        public decimal ActualTotal
        {
            get => _actualTotal;
            set => SetProperty(ref _actualTotal, value);
        }

        public decimal DifferenceTotal
        {
            get => _differenceTotal;
            set => SetProperty(ref _differenceTotal, value);
        }

        public int UnclosedCount
        {
            get => _unclosedCount;
            set => SetProperty(ref _unclosedCount, value);
        }

        public int CheckedTargetCount
        {
            get => _checkedTargetCount;
            private set
            {
                if (SetProperty(ref _checkedTargetCount, value))
                {
                    OnPropertyChanged(nameof(CanCreateBundle));
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public bool CanCreateBundle => CheckedTargetCount >= MinimumBundleTargetCount;

        public async Task InitializeAsync()
        {
            ResetDefaultDateRange();

            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            await RunWithLoadingAsync(LoadSearchDataAsync);
        }

        private async Task LoadSearchDataAsync()
        {
            await LoadCostGroupsAsync();
            await LoadTargetsAsync();
        }

        private async Task ResetAsync()
        {
            ResetDefaultSearchConditions();
            ClearCostInput();

            await SearchAsync();
        }

        private void ResetDefaultSearchConditions()
        {
            ResetDefaultDateRange();
            UseSettlementMonth = true;
            SelectedProcessType = OutsourceProcessingCostDisplayOptions.CutProcessTypeCode;
            SelectedStatusCode = OutsourceProcessingCostDisplayOptions.AllStatusCode;
            SearchKeyword = string.Empty;
        }

        private void ResetDefaultDateRange()
        {
            var today = DateTime.Today;
            SettlementMonth = new DateTime(today.Year, today.Month, 1);
            ActualBillingMonth = SettlementMonth;
            DateFrom = today.AddMonths(-1);
            DateTo = today;
        }

        private async Task LoadTargetsAsync()
        {
            var result = await _apiClient.GetAsync<OutsourceProcessingCostTargetListDto>(BuildTargetUrl());

            ReplaceTargets(null);
            SelectedTarget = null;

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "외주가공비 등록 대상 조회에 실패했습니다.");
                return;
            }

            ReplaceTargets(result.Data.Items.Select(OutsourceProcessingCostTargetRowModel.FromDto));
        }

        private async Task LoadCostGroupsAsync()
        {
            var result = await _apiClient.GetAsync<OutsourceProcessingCostGroupListDto>(BuildCostGroupUrl());

            ReplaceCostGroups(null);
            SelectedCostGroup = null;
            ReplaceAllocations(null);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "외주가공비 목록 조회에 실패했습니다.");
                ResetCostGroupSummary();
                return;
            }

            ReplaceCostGroups(result.Data.Items.Select(OutsourceProcessingCostGroupRowModel.FromDto));
            ApplyCostGroupSummary(result.Data);
        }

        private void ReplaceTargets(IEnumerable<OutsourceProcessingCostTargetRowModel>? targets)
        {
            foreach (var target in Targets)
            {
                target.PropertyChanged -= Target_PropertyChanged;
            }

            Targets.Clear();

            if (targets != null)
            {
                foreach (var target in targets)
                {
                    target.PropertyChanged += Target_PropertyChanged;
                    Targets.Add(target);
                }
            }

            UpdateCheckedTargetCount();
        }

        private void ReplaceCostGroups(IEnumerable<OutsourceProcessingCostGroupRowModel>? costGroups)
        {
            CostGroups.Clear();

            if (costGroups == null)
            {
                return;
            }

            foreach (var costGroup in costGroups)
            {
                CostGroups.Add(costGroup);
            }
        }

        private void ApplyCostGroupSummary(OutsourceProcessingCostGroupListDto summary)
        {
            TotalCount = summary.TotalCount;
            StandardTotal = summary.StandardTotal;
            ActualTotal = summary.ActualTotal;
            DifferenceTotal = summary.DifferenceTotal;
            UnclosedCount = summary.UnclosedCount;
        }

        private void ResetCostGroupSummary()
        {
            TotalCount = 0;
            StandardTotal = 0;
            ActualTotal = 0;
            DifferenceTotal = 0;
            UnclosedCount = 0;
        }

        private async Task CreateGroupAsync()
        {
            var selectedTargets = Targets.Where(x => x.IsChecked).ToList();

            if (selectedTargets.Count < MinimumBundleTargetCount)
            {
                _messageService.ShowWarning("가공비 묶음에 포함할 대상을 선택하세요.");
                return;
            }

            if (!EnsureSettlementMonthSelected())
            {
                return;
            }

            if (!EnsureTargetsNotActiveRegistered(selectedTargets, "이미 비용묶음에 포함된 대상이 있습니다."))
            {
                return;
            }

            var request = BuildSaveRequest(selectedTargets);

            if (!_messageService.Confirm($"선택한 {selectedTargets.Count}건으로 가공비 묶음을 생성하시겠습니까?"))
            {
                return;
            }

            await CreateCostGroupAsync(
                request,
                "가공비 묶음이 생성되었습니다.",
                "가공비 묶음 생성에 실패했습니다.");
        }

        private async Task SaveCostAsync()
        {
            if (SelectedTarget == null)
            {
                _messageService.ShowWarning("가공비를 등록할 행을 선택하세요.");
                return;
            }

            if (!EnsureSettlementMonthSelected())
            {
                return;
            }

            if (SelectedCostGroup == null)
            {
                if (!EnsureTargetNotActiveRegistered(SelectedTarget, "이미 등록된 대상입니다."))
                {
                    return;
                }

                await CreateSingleCostGroupAsync(SelectedTarget);
                return;
            }

            if (!SelectedCostGroup.CanEdit)
            {
                _messageService.ShowWarning("작성중 상태의 가공비 묶음만 수정할 수 있습니다.");
                return;
            }

            await UpdateCostGroupAsync(SelectedCostGroup);
        }

        private bool EnsureSettlementMonthSelected()
        {
            if (SettlementMonth.HasValue)
            {
                return true;
            }

            _messageService.ShowWarning("정산기준월을 선택하세요.");
            return false;
        }

        private bool EnsureTargetsNotActiveRegistered(
            IEnumerable<OutsourceProcessingCostTargetRowModel> targets,
            string warningPrefix)
        {
            var activeRegistered = targets.FirstOrDefault(x => x.IsActiveRegistered);
            return activeRegistered == null || EnsureTargetNotActiveRegistered(activeRegistered, warningPrefix);
        }

        private bool EnsureTargetNotActiveRegistered(
            OutsourceProcessingCostTargetRowModel target,
            string warningPrefix)
        {
            if (!target.IsActiveRegistered)
            {
                return true;
            }

            _messageService.ShowWarning($"{warningPrefix} 비용묶음: {target.AlreadyCostGroupNo}");
            return false;
        }

        private async Task UpdateCostGroupAsync(OutsourceProcessingCostGroupRowModel costGroup)
        {
            await RunWithLoadingAsync(async () =>
            {
                var url = OutsourceProcessingCostQueryBuilder.BuildCostGroupDetailUrl(
                    costGroup.OutsourceProcessingCostGroupId);
                var result = await _apiClient.PatchAsync<OutsourceProcessingCostSaveRequest, OutsourceProcessingCostGroupDto>(
                    url,
                    BuildSaveRequest());

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "가공비 저장에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("가공비가 저장되었습니다.");
                await LoadSearchDataAsync();
            });
        }

        private async Task CloseAsync()
        {
            if (SelectedCostGroup == null)
            {
                return;
            }

            if (ActualAmount == null)
            {
                _messageService.ShowWarning("실제가공비 입력 후 월마감할 수 있습니다.");
                return;
            }

            if (!_messageService.Confirm(BuildCloseConfirmMessage(SelectedCostGroup)))
            {
                return;
            }

            await PostCostGroupStatusAsync(SelectedCostGroup, CloseAction, "월마감 처리되었습니다.");
        }

        private async Task ReopenAsync()
        {
            if (SelectedCostGroup == null)
            {
                return;
            }

            if (!ConfirmCostGroupAction(SelectedCostGroup, "마감을 취소하시겠습니까?"))
            {
                return;
            }

            await PostCostGroupStatusAsync(SelectedCostGroup, ReopenAction, "마감취소 처리되었습니다.");
        }

        private async Task CancelAsync()
        {
            if (SelectedCostGroup == null)
            {
                return;
            }

            if (!ConfirmCostGroupAction(SelectedCostGroup, "가공비 묶음을 취소처리하시겠습니까?"))
            {
                return;
            }

            await PostCostGroupStatusAsync(SelectedCostGroup, CancelAction, "취소처리되었습니다.");
        }

        private bool ConfirmCostGroupAction(OutsourceProcessingCostGroupRowModel costGroup, string message)
        {
            return _messageService.Confirm($"[{costGroup.CostGroupNo}] {message}");
        }

        private static string BuildCloseConfirmMessage(OutsourceProcessingCostGroupRowModel costGroup)
        {
            return costGroup.AmountDifference.HasValue && costGroup.AmountDifference.Value != 0
                ? $"[{costGroup.CostGroupNo}] 원가차액 {costGroup.AmountDifference.Value:N0}원이 있습니다. 확인 후 월마감을 확정하시겠습니까?"
                : $"[{costGroup.CostGroupNo}] 월마감을 확정하시겠습니까?";
        }

        private async Task PostCostGroupStatusAsync(
            OutsourceProcessingCostGroupRowModel costGroup,
            string action,
            string successMessage)
        {
            await RunWithLoadingAsync(async () =>
            {
                var url = OutsourceProcessingCostQueryBuilder.BuildCostGroupStatusUrl(
                    costGroup.OutsourceProcessingCostGroupId,
                    action);
                var result = await _apiClient.PostAsync<object, OutsourceProcessingCostGroupDto>(url, new { });

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "상태 처리에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo(successMessage);
                await LoadSearchDataAsync();
            });
        }

        private OutsourceProcessingCostSaveRequest BuildSaveRequest()
        {
            return OutsourceProcessingCostSaveRequestBuilder.Build(
                SettlementMonth,
                SelectedProcessType,
                StandardAmount,
                StandardMemo,
                ActualAmount,
                ActualBillingMonth,
                ActualMemo,
                Remark);
        }

        private OutsourceProcessingCostSaveRequest BuildSaveRequest(IEnumerable<OutsourceProcessingCostTargetRowModel> targets)
        {
            return OutsourceProcessingCostSaveRequestBuilder.BuildForTargets(
                SettlementMonth,
                SelectedProcessType,
                StandardAmount,
                StandardMemo,
                ActualAmount,
                ActualBillingMonth,
                ActualMemo,
                Remark,
                targets);
        }

        private async Task CreateSingleCostGroupAsync(OutsourceProcessingCostTargetRowModel target)
        {
            await CreateCostGroupAsync(
                BuildSaveRequest(new[] { target }),
                "가공비가 저장되었습니다.",
                "가공비 등록에 실패했습니다.");
        }

        private async Task CreateCostGroupAsync(
            OutsourceProcessingCostSaveRequest request,
            string successMessage,
            string fallbackErrorMessage)
        {
            await RunWithLoadingAsync(async () =>
            {
                var result = await _apiClient.PostAsync<OutsourceProcessingCostSaveRequest, OutsourceProcessingCostGroupDto>(
                    OutsourceProcessingCostQueryBuilder.BuildCostGroupCollectionUrl(),
                    request);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? fallbackErrorMessage);
                    return;
                }

                _messageService.ShowInfo(successMessage);
                await LoadSearchDataAsync();
            });
        }

        private async Task RunWithLoadingAsync(Func<Task> action)
        {
            try
            {
                IsLoading = true;
                await action();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildTargetUrl()
        {
            NormalizeSearchConditions();
            return OutsourceProcessingCostQueryBuilder.BuildTargetUrl(
                SelectedProcessType,
                DateFrom,
                DateTo,
                SelectedStatusCode,
                SearchKeyword);
        }

        private string BuildCostGroupUrl()
        {
            NormalizeSearchConditions();
            return OutsourceProcessingCostQueryBuilder.BuildCostGroupUrl(
                SelectedProcessType,
                UseSettlementMonth,
                SettlementMonth,
                SelectedStatusCode,
                SearchKeyword);
        }

        private void LoadSelectedTarget(OutsourceProcessingCostTargetRowModel? target)
        {
            if (target?.OutsourceProcessingCostGroupId == null)
            {
                SelectedCostGroup = null;
                LoadTargetAllocationPreview(target);
                return;
            }

            var costGroup = CostGroups.FirstOrDefault(
                x => x.OutsourceProcessingCostGroupId == target.OutsourceProcessingCostGroupId.Value);
            SelectedCostGroup = costGroup;

            if (costGroup == null)
            {
                LoadTargetAllocationPreview(target);
            }
        }

        private void LoadTargetAllocationPreview(OutsourceProcessingCostTargetRowModel? target)
        {
            ReplaceAllocations(target?.Allocations);
        }

        private void LoadSelectedCostGroup(OutsourceProcessingCostGroupRowModel? item)
        {
            if (item == null)
            {
                ClearCostInput();
                return;
            }

            LoadCostInput(item);
            ReplaceAllocations(item.Allocations);
        }

        private void LoadCostInput(OutsourceProcessingCostGroupRowModel item)
        {
            StandardAmount = item.StandardAmount;
            StandardMemo = item.StandardMemo ?? string.Empty;
            ActualAmount = item.ActualAmount;
            ActualBillingMonth = item.ActualBillingMonth ?? SettlementMonth;
            ActualMemo = item.ActualMemo ?? string.Empty;
            Remark = item.Remark ?? string.Empty;
        }

        private void ClearCostInput()
        {
            StandardAmount = null;
            StandardMemo = string.Empty;
            ActualAmount = null;
            ActualBillingMonth = SettlementMonth;
            ActualMemo = string.Empty;
            Remark = string.Empty;
            ReplaceAllocations(null);
        }

        private void ReplaceAllocations(IEnumerable<OutsourceProcessingCostAllocationRowModel>? allocations)
        {
            Allocations.Clear();

            if (allocations == null)
            {
                return;
            }

            foreach (var allocation in allocations)
            {
                Allocations.Add(allocation);
            }
        }

        private void Target_PropertyChanged(object? sender, PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(OutsourceProcessingCostTargetRowModel.IsChecked))
            {
                UpdateCheckedTargetCount();
            }
        }

        private void UpdateCheckedTargetCount()
        {
            CheckedTargetCount = Targets.Count(x => x.IsChecked);
        }

        private void NormalizeSearchConditions()
        {
            SelectedProcessType = (SelectedProcessType ?? OutsourceProcessingCostDisplayOptions.CutProcessTypeCode)
                .Trim()
                .ToUpperInvariant();
            SelectedStatusCode = string.IsNullOrWhiteSpace(SelectedStatusCode)
                ? OutsourceProcessingCostDisplayOptions.AllStatusCode
                : SelectedStatusCode.Trim().ToUpperInvariant();
            SearchKeyword = SearchKeyword?.Trim() ?? string.Empty;
        }

        private static DateTime? NormalizeMonth(DateTime? value)
        {
            if (!value.HasValue)
            {
                return null;
            }

            return new DateTime(value.Value.Year, value.Value.Month, 1);
        }

        private void RaiseCommandCanExecuteChanged()
        {
            foreach (var command in new[]
            {
                SearchCommand,
                ResetCommand,
                CreateGroupCommand,
                SaveCostCommand,
                CloseCommand,
                ReopenCommand,
                CancelCommand
            })
            {
                command.RaiseCanExecuteChanged();
            }
        }

    }

}
