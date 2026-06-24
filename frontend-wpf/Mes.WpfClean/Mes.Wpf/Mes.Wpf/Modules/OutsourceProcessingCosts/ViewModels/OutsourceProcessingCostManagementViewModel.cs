using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceProcessingCosts.Dtos;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.ViewModels
{
    public class OutsourceProcessingCostManagementViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private DateTime? _settlementMonth;
        private bool _useSettlementMonth = true;
        private DateTime? _dateFrom;
        private DateTime? _dateTo;
        private string _selectedProcessType = "CUT";
        private string _selectedStatusCode = "ALL";
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

            ProcessTypeOptions = new ObservableCollection<CodeNameOption>
            {
                new("CUT", "재단"),
                new("PRINT", "인쇄"),
                new("DIECUT", "도무송")
            };
            StatusOptions = new ObservableCollection<CodeNameOption>
            {
                new("ALL", "전체"),
                new("UNREGISTERED", "미등록"),
                new("DRAFT", "작성중"),
                new("COST_VARIANCE", "원가차액"),
                new("CLOSED", "월마감"),
                new("CANCELED", "취소")
            };
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

        public ICommand SearchCommand { get; }
        public ICommand ResetCommand { get; }
        public ICommand CreateGroupCommand { get; }
        public ICommand SaveCostCommand { get; }
        public ICommand CloseCommand { get; }
        public ICommand ReopenCommand { get; }
        public ICommand CancelCommand { get; }

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

        public bool CanCreateBundle => CheckedTargetCount >= 2;

        public async Task InitializeAsync()
        {
            var today = DateTime.Today;
            SettlementMonth = new DateTime(today.Year, today.Month, 1);
            ActualBillingMonth = SettlementMonth;
            DateFrom = today.AddMonths(-1);
            DateTo = today;

            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            try
            {
                IsLoading = true;
                await LoadCostGroupsAsync();
                await LoadTargetsAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task ResetAsync()
        {
            var today = DateTime.Today;
            SettlementMonth = new DateTime(today.Year, today.Month, 1);
            UseSettlementMonth = true;
            DateFrom = today.AddMonths(-1);
            DateTo = today;
            SelectedProcessType = "CUT";
            SelectedStatusCode = "ALL";
            SearchKeyword = string.Empty;
            ClearCostInput();

            await SearchAsync();
        }

        private async Task LoadTargetsAsync()
        {
            var result = await _apiClient.GetAsync<OutsourceProcessingCostTargetListDto>(BuildTargetUrl());

            Targets.Clear();
            SelectedTarget = null;

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "외주가공비 등록 대상 조회에 실패했습니다.");
                return;
            }

            foreach (var item in result.Data.Items)
            {
                var target = OutsourceProcessingCostTargetRowModel.FromDto(item);
                target.PropertyChanged += Target_PropertyChanged;
                Targets.Add(target);
            }

            UpdateCheckedTargetCount();
        }

        private async Task LoadCostGroupsAsync()
        {
            var result = await _apiClient.GetAsync<OutsourceProcessingCostGroupListDto>(BuildCostGroupUrl());

            CostGroups.Clear();
            SelectedCostGroup = null;
            Allocations.Clear();

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "외주가공비 목록 조회에 실패했습니다.");
                TotalCount = 0;
                StandardTotal = 0;
                ActualTotal = 0;
                DifferenceTotal = 0;
                UnclosedCount = 0;
                return;
            }

            foreach (var item in result.Data.Items)
            {
                CostGroups.Add(OutsourceProcessingCostGroupRowModel.FromDto(item));
            }

            TotalCount = result.Data.TotalCount;
            StandardTotal = result.Data.StandardTotal;
            ActualTotal = result.Data.ActualTotal;
            DifferenceTotal = result.Data.DifferenceTotal;
            UnclosedCount = result.Data.UnclosedCount;
        }

        private async Task CreateGroupAsync()
        {
            var selectedTargets = Targets.Where(x => x.IsChecked).ToList();

            if (selectedTargets.Count < 2)
            {
                _messageService.ShowWarning("가공비 묶음에 포함할 대상을 선택하세요.");
                return;
            }

            if (!SettlementMonth.HasValue)
            {
                _messageService.ShowWarning("정산기준월을 선택하세요.");
                return;
            }

            var activeRegistered = selectedTargets.FirstOrDefault(x => x.IsActiveRegistered);
            if (activeRegistered != null)
            {
                _messageService.ShowWarning($"이미 비용묶음에 포함된 대상이 있습니다. 비용묶음: {activeRegistered.AlreadyCostGroupNo}");
                return;
            }

            var request = BuildSaveRequest(selectedTargets);

            if (!_messageService.Confirm($"선택한 {selectedTargets.Count}건으로 가공비 묶음을 생성하시겠습니까?"))
            {
                return;
            }

            try
            {
                IsLoading = true;
                var result = await _apiClient.PostAsync<OutsourceProcessingCostSaveRequest, OutsourceProcessingCostGroupDto>(
                    ApiRoutes.OutsourceProcessingCosts,
                    request);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "가공비 묶음 생성에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("가공비 묶음이 생성되었습니다.");
                await SearchAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task SaveCostAsync()
        {
            if (SelectedTarget == null)
            {
                _messageService.ShowWarning("가공비를 등록할 행을 선택하세요.");
                return;
            }

            if (!SettlementMonth.HasValue)
            {
                _messageService.ShowWarning("정산기준월을 선택하세요.");
                return;
            }

            if (SelectedCostGroup == null)
            {
                if (SelectedTarget.IsActiveRegistered)
                {
                    _messageService.ShowWarning($"이미 등록된 대상입니다. 비용묶음: {SelectedTarget.AlreadyCostGroupNo}");
                    return;
                }

                await CreateSingleCostGroupAsync(SelectedTarget);
                return;
            }

            if (SelectedCostGroup == null)
            {
                _messageService.ShowWarning("먼저 등록대상에서 비용묶음이 생성된 행을 선택하세요.");
                return;
            }

            if (!SelectedCostGroup.CanEdit)
            {
                _messageService.ShowWarning("작성중 상태의 가공비 묶음만 수정할 수 있습니다.");
                return;
            }

            try
            {
                IsLoading = true;
                var url = $"{ApiRoutes.OutsourceProcessingCosts}/{SelectedCostGroup.OutsourceProcessingCostGroupId}";
                var result = await _apiClient.PatchAsync<OutsourceProcessingCostSaveRequest, OutsourceProcessingCostGroupDto>(
                    url,
                    BuildSaveRequest());

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "가공비 저장에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("가공비가 저장되었습니다.");
                await SearchAsync();
            }
            finally
            {
                IsLoading = false;
            }
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

            var confirmMessage = SelectedCostGroup.AmountDifference.HasValue
                && SelectedCostGroup.AmountDifference.Value != 0
                ? $"[{SelectedCostGroup.CostGroupNo}] 원가차액 {SelectedCostGroup.AmountDifference.Value:N0}원이 있습니다. 확인 후 월마감을 확정하시겠습니까?"
                : $"[{SelectedCostGroup.CostGroupNo}] 월마감을 확정하시겠습니까?";

            if (!_messageService.Confirm(confirmMessage))
            {
                return;
            }

            await PostStatusAsync($"{ApiRoutes.OutsourceProcessingCosts}/{SelectedCostGroup.OutsourceProcessingCostGroupId}/close", "월마감 처리되었습니다.");
        }

        private async Task ReopenAsync()
        {
            if (SelectedCostGroup == null)
            {
                return;
            }

            if (!_messageService.Confirm($"[{SelectedCostGroup.CostGroupNo}] 마감을 취소하시겠습니까?"))
            {
                return;
            }

            await PostStatusAsync($"{ApiRoutes.OutsourceProcessingCosts}/{SelectedCostGroup.OutsourceProcessingCostGroupId}/reopen", "마감취소 처리되었습니다.");
        }

        private async Task CancelAsync()
        {
            if (SelectedCostGroup == null)
            {
                return;
            }

            if (!_messageService.Confirm($"[{SelectedCostGroup.CostGroupNo}] 가공비 묶음을 취소처리하시겠습니까?"))
            {
                return;
            }

            await PostStatusAsync($"{ApiRoutes.OutsourceProcessingCosts}/{SelectedCostGroup.OutsourceProcessingCostGroupId}/cancel", "취소처리되었습니다.");
        }

        private async Task PostStatusAsync(string url, string successMessage)
        {
            try
            {
                IsLoading = true;
                var result = await _apiClient.PostAsync<object, OutsourceProcessingCostGroupDto>(url, new { });

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "상태 처리에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo(successMessage);
                await SearchAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private OutsourceProcessingCostSaveRequest BuildSaveRequest()
        {
            return new OutsourceProcessingCostSaveRequest
            {
                SettlementMonth = NormalizeMonth(SettlementMonth) ?? DateTime.Today,
                ProcessType = SelectedProcessType,
                StandardAmount = StandardAmount,
                StandardMemo = EmptyToNull(StandardMemo),
                ActualAmount = ActualAmount,
                ActualBillingMonth = NormalizeMonth(ActualBillingMonth),
                ActualMemo = EmptyToNull(ActualMemo),
                Remark = EmptyToNull(Remark)
            };
        }

        private OutsourceProcessingCostSaveRequest BuildSaveRequest(IEnumerable<OutsourceProcessingCostTargetRowModel> targets)
        {
            var request = BuildSaveRequest();
            var selectedTargets = targets.ToList();

            request.TargetWorkGroupIds = selectedTargets
                .Where(x => x.OutsourceWorkGroupId.HasValue)
                .Select(x => x.OutsourceWorkGroupId!.Value)
                .ToList();
            request.TargetLotIds = selectedTargets
                .Where(x => x.LotId.HasValue)
                .Select(x => x.LotId!.Value)
                .ToList();

            return request;
        }

        private async Task CreateSingleCostGroupAsync(OutsourceProcessingCostTargetRowModel target)
        {
            try
            {
                IsLoading = true;
                var result = await _apiClient.PostAsync<OutsourceProcessingCostSaveRequest, OutsourceProcessingCostGroupDto>(
                    ApiRoutes.OutsourceProcessingCosts,
                    BuildSaveRequest(new[] { target }));

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "가공비 등록에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("가공비가 저장되었습니다.");
                await SearchAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildTargetUrl()
        {
            NormalizeSearchConditions();
            var query = new List<string>
            {
                $"process_type={Uri.EscapeDataString(SelectedProcessType)}"
            };

            if (DateFrom.HasValue)
            {
                query.Add($"date_from={DateFrom.Value:yyyy-MM-dd}");
            }

            if (DateTo.HasValue)
            {
                query.Add($"date_to={DateTo.Value:yyyy-MM-dd}");
            }

            if (SelectedStatusCode != "ALL")
            {
                query.Add($"status={Uri.EscapeDataString(SelectedStatusCode)}");
            }

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(SearchKeyword)}");
            }

            return $"{ApiRoutes.OutsourceProcessingCostTargets}?{string.Join("&", query)}";
        }

        private string BuildCostGroupUrl()
        {
            NormalizeSearchConditions();
            var query = new List<string>
            {
                $"process_type={Uri.EscapeDataString(SelectedProcessType)}"
            };

            if (UseSettlementMonth && SettlementMonth.HasValue)
            {
                query.Add($"settlement_month={SettlementMonth.Value:yyyy-MM-dd}");
            }

            if (SelectedStatusCode is "DRAFT" or "CLOSED" or "CANCELED" or "COST_VARIANCE")
            {
                query.Add($"status={Uri.EscapeDataString(SelectedStatusCode)}");
            }

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(SearchKeyword)}");
            }

            return $"{ApiRoutes.OutsourceProcessingCosts}?{string.Join("&", query)}";
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
            Allocations.Clear();

            if (target == null)
            {
                return;
            }

            foreach (var allocation in target.Allocations)
            {
                Allocations.Add(allocation);
            }
        }

        private void LoadSelectedCostGroup(OutsourceProcessingCostGroupRowModel? item)
        {
            Allocations.Clear();

            if (item == null)
            {
                ClearCostInput();
                return;
            }

            StandardAmount = item.StandardAmount;
            StandardMemo = item.StandardMemo ?? string.Empty;
            ActualAmount = item.ActualAmount;
            ActualBillingMonth = item.ActualBillingMonth ?? SettlementMonth;
            ActualMemo = item.ActualMemo ?? string.Empty;
            Remark = item.Remark ?? string.Empty;

            foreach (var allocation in item.Allocations)
            {
                Allocations.Add(allocation);
            }
        }

        private void ClearCostInput()
        {
            StandardAmount = null;
            StandardMemo = string.Empty;
            ActualAmount = null;
            ActualBillingMonth = SettlementMonth;
            ActualMemo = string.Empty;
            Remark = string.Empty;
            Allocations.Clear();
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
            SelectedProcessType = (SelectedProcessType ?? "CUT").Trim().ToUpperInvariant();
            SelectedStatusCode = string.IsNullOrWhiteSpace(SelectedStatusCode)
                ? "ALL"
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

        private static string? EmptyToNull(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
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
                if (command is AsyncRelayCommand asyncCommand)
                {
                    asyncCommand.RaiseCanExecuteChanged();
                }
            }
        }
    }

    public record CodeNameOption(string Code, string Name);

    public class OutsourceProcessingCostTargetRowModel : BindableBase
    {
        private bool _isChecked;

        public bool IsChecked
        {
            get => _isChecked;
            set => SetProperty(ref _isChecked, value);
        }

        public string TargetKey { get; set; } = string.Empty;
        public string ProcessType { get; set; } = string.Empty;
        public string ProcessTypeName => DisplayProcessName(ProcessType);
        public long? OutsourceWorkGroupId { get; set; }
        public long? LotId { get; set; }
        public string? InstructionNo { get; set; }
        public DateTime? InstructionDate { get; set; }
        public string? PartnerName { get; set; }
        public string? GroupSeq { get; set; }
        public bool IsBundle { get; set; }
        public int LotCount { get; set; }
        public string? RepresentativeLotNo { get; set; }
        public string LotNosText { get; set; } = string.Empty;
        public string ProductNamesText { get; set; } = string.Empty;
        public string ProductSpecText { get; set; } = string.Empty;
        public long? SheetQty { get; set; }
        public long? InstructionOutputQty { get; set; }
        public string AllocationBasisType { get; set; } = string.Empty;
        public decimal AllocationBasisValue { get; set; }
        public long? OutsourceProcessingCostGroupId { get; set; }
        public string? AlreadyCostGroupNo { get; set; }
        public string? CostStatusCode { get; set; }
        public string CostStatusName => string.IsNullOrWhiteSpace(CostStatusCode)
            ? "미등록"
            : IsCostVariance
                ? "원가차액"
            : DisplayStatusName(CostStatusCode);
        public string StatusVisualCode => IsCostVariance
            ? "COST_VARIANCE"
            : string.IsNullOrWhiteSpace(CostStatusCode)
                ? "UNREGISTERED"
                : CostStatusCode;
        public decimal? StandardAmount { get; set; }
        public decimal? ActualAmount { get; set; }
        public decimal? AmountDifference { get; set; }
        public DateTime? SettlementMonth { get; set; }
        public List<OutsourceProcessingCostAllocationRowModel> Allocations { get; set; } = new();
        public bool IsActiveRegistered => CostStatusCode is "DRAFT" or "CLOSED";
        public bool IsCostVariance =>
            CostStatusCode == "DRAFT"
            && StandardAmount.HasValue
            && ActualAmount.HasValue
            && AmountDifference.HasValue
            && AmountDifference.Value != 0;

        public static OutsourceProcessingCostTargetRowModel FromDto(OutsourceProcessingCostTargetDto dto)
        {
            return new OutsourceProcessingCostTargetRowModel
            {
                TargetKey = dto.TargetKey,
                ProcessType = dto.ProcessType,
                OutsourceWorkGroupId = dto.OutsourceWorkGroupId,
                LotId = dto.LotId,
                InstructionNo = dto.InstructionNo,
                InstructionDate = dto.InstructionDate,
                PartnerName = dto.PartnerName,
                GroupSeq = dto.GroupSeq,
                IsBundle = dto.IsBundle,
                LotCount = dto.LotCount,
                RepresentativeLotNo = dto.RepresentativeLotNo,
                LotNosText = !string.IsNullOrWhiteSpace(dto.RepresentativeLotNo)
                    ? dto.RepresentativeLotNo
                    : string.Join(", ", dto.LotNos),
                ProductNamesText = !string.IsNullOrWhiteSpace(dto.RepresentativeProductName)
                    ? dto.RepresentativeProductName
                    : string.Join(", ", dto.ProductNames),
                ProductSpecText = string.Join(", ", dto.ProductSpecs),
                SheetQty = dto.SheetQty,
                InstructionOutputQty = dto.InstructionOutputQty,
                AllocationBasisType = dto.AllocationBasisType == "AREA" ? "면적" : "수량",
                AllocationBasisValue = dto.AllocationBasisValue,
                OutsourceProcessingCostGroupId = dto.OutsourceProcessingCostGroupId,
                AlreadyCostGroupNo = dto.AlreadyCostGroupNo,
                CostStatusCode = dto.CostStatus,
                StandardAmount = dto.StandardAmount,
                ActualAmount = dto.ActualAmount,
                AmountDifference = dto.AmountDifference,
                SettlementMonth = dto.SettlementMonth,
                Allocations = dto.Allocations
                    .Select(OutsourceProcessingCostAllocationRowModel.FromDto)
                    .ToList()
            };
        }

        private static string DisplayProcessName(string processType)
        {
            return processType switch
            {
                "CUT" => "재단",
                "PRINT" => "인쇄",
                "DIECUT" => "도무송",
                _ => processType
            };
        }

        private static string DisplayStatusName(string status)
        {
            return status switch
            {
                "DRAFT" => "작성중",
                "COST_VARIANCE" => "원가차액",
                "CLOSED" => "월마감",
                "CANCELED" => "취소",
                _ => status
            };
        }
    }

    public class OutsourceProcessingCostGroupRowModel
    {
        public long OutsourceProcessingCostGroupId { get; set; }
        public string CostGroupNo { get; set; } = string.Empty;
        public DateTime SettlementMonth { get; set; }
        public string ProcessType { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public bool CanEdit => Status == "DRAFT";
        public decimal? StandardAmount { get; set; }
        public decimal? ActualAmount { get; set; }
        public decimal? AmountDifference { get; set; }
        public string? StandardMemo { get; set; }
        public DateTime? ActualBillingMonth { get; set; }
        public string? ActualMemo { get; set; }
        public string? Remark { get; set; }
        public List<OutsourceProcessingCostAllocationRowModel> Allocations { get; set; } = new();

        public static OutsourceProcessingCostGroupRowModel FromDto(OutsourceProcessingCostGroupDto dto)
        {
            return new OutsourceProcessingCostGroupRowModel
            {
                OutsourceProcessingCostGroupId = dto.OutsourceProcessingCostGroupId,
                CostGroupNo = dto.CostGroupNo,
                SettlementMonth = dto.SettlementMonth,
                ProcessType = dto.ProcessType,
                Status = dto.Status,
                StandardAmount = dto.StandardAmount,
                ActualAmount = dto.ActualAmount,
                AmountDifference = dto.AmountDifference,
                StandardMemo = dto.StandardMemo,
                ActualBillingMonth = dto.ActualBillingMonth,
                ActualMemo = dto.ActualMemo,
                Remark = dto.Remark,
                Allocations = dto.Allocations
                    .Select(OutsourceProcessingCostAllocationRowModel.FromDto)
                    .ToList()
            };
        }
    }

    public class OutsourceProcessingCostAllocationRowModel
    {
        public string LotNo { get; set; } = string.Empty;
        public string? ProductName { get; set; }
        public string ProductSpecText { get; set; } = string.Empty;
        public int? CutsPerSheet { get; set; }
        public long? SheetQty { get; set; }
        public long? InstructionOutputQty { get; set; }
        public string BasisTypeName { get; set; } = string.Empty;
        public decimal BasisValue { get; set; }
        public decimal? BasisAreaSqm { get; set; }
        public decimal AllocationRatioPercent { get; set; }
        public decimal? StandardAllocatedAmount { get; set; }
        public decimal? ActualAllocatedAmount { get; set; }
        public decimal? AmountDifference { get; set; }

        public static OutsourceProcessingCostAllocationRowModel FromDto(OutsourceProcessingCostAllocationDto dto)
        {
            return new OutsourceProcessingCostAllocationRowModel
            {
                LotNo = dto.LotNo,
                ProductName = dto.ProductName,
                ProductSpecText = BuildSpecText(dto),
                CutsPerSheet = dto.CutsPerSheet,
                SheetQty = dto.SheetQty,
                InstructionOutputQty = dto.InstructionOutputQty,
                BasisTypeName = dto.BasisType == "AREA" ? "면적" : "수량",
                BasisValue = dto.BasisValue,
                BasisAreaSqm = dto.BasisAreaSqm,
                AllocationRatioPercent = dto.AllocationRatio * 100,
                StandardAllocatedAmount = dto.StandardAllocatedAmount,
                ActualAllocatedAmount = dto.ActualAllocatedAmount,
                AmountDifference = dto.AmountDifference
            };
        }

        private static string BuildSpecText(OutsourceProcessingCostAllocationDto dto)
        {
            if (dto.PanelWidthMm.HasValue && dto.PanelLengthMm.HasValue)
            {
                return $"{dto.PanelWidthMm}x{dto.PanelLengthMm}";
            }

            return dto.ProductSpec ?? string.Empty;
        }
    }
}
