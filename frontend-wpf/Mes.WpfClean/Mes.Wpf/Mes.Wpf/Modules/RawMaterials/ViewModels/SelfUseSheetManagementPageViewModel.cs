using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using Mes.Wpf.Modules.Partners.Dtos;
using Mes.Wpf.Modules.RawMaterials.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.RawMaterials.ViewModels
{
    public class SelfUseSheetManagementPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private SelfUseSheetJobDto? _selectedJob;
        private RawMaterialInventoryLotDto? _selectedSourceLot;
        private PartnerDto? _selectedVendor;
        private SelfUseSheetOption? _selectedPurpose;
        private SelfUseSheetOption? _selectedExecution;
        private SelfUseSheetOption? _selectedStatusFilter;
        private SelfUseSheetOption? _selectedPurposeFilter;
        private string _searchKeyword = string.Empty;
        private decimal _plannedInputQty;
        private decimal _cutWidthMm;
        private decimal _cutLengthMm;
        private long _plannedOutputQty;
        private decimal _expectedProcessingFee;
        private string _memo = string.Empty;
        private long _producedQty;
        private long _scrapQty;
        private decimal _actualProcessingFee;
        private string _completionMemo = string.Empty;
        private string _cancellationReason = string.Empty;

        public SelfUseSheetManagementPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            Jobs = new ObservableCollection<SelfUseSheetJobDto>();
            SourceLots = new ObservableCollection<RawMaterialInventoryLotDto>();
            Vendors = new ObservableCollection<PartnerDto>();
            PurposeOptions = new ObservableCollection<SelfUseSheetOption>
            {
                new("PRINT_SETUP", "인쇄 초기 셋팅"),
                new("SAMPLE", "샘플 제작"),
                new("TEST_RND", "시험/개발"),
                new("OTHER", "기타")
            };
            ExecutionOptions = new ObservableCollection<SelfUseSheetOption>
            {
                new("INTERNAL", "내부 재단"),
                new("OUTSOURCE", "외주 재단")
            };
            StatusOptions = new ObservableCollection<SelfUseSheetOption>
            {
                new(string.Empty, "전체"),
                new("DRAFT", "임시저장"),
                new("IN_PROGRESS", "가공중"),
                new("COMPLETED", "완료"),
                new("CANCELED", "취소")
            };
            PurposeFilterOptions = new ObservableCollection<SelfUseSheetOption>(
                new[] { new SelfUseSheetOption(string.Empty, "전체") }.Concat(PurposeOptions));
            _selectedPurpose = PurposeOptions[0];
            _selectedExecution = ExecutionOptions[1];
            _selectedStatusFilter = StatusOptions[0];
            _selectedPurposeFilter = PurposeFilterOptions[0];

            RefreshCommand = new AsyncRelayCommand(LoadJobsAsync);
            CreateCommand = new AsyncRelayCommand(CreateAsync);
            StartCommand = new AsyncRelayCommand(StartAsync, () => SelectedJob?.Status == "DRAFT");
            CompleteCommand = new AsyncRelayCommand(CompleteAsync, () => SelectedJob?.Status == "IN_PROGRESS");
            CancelCommand = new AsyncRelayCommand(
                CancelAsync,
                () => SelectedJob != null && SelectedJob.Status != "CANCELED");
            ClearCommand = new AsyncRelayCommand(() =>
            {
                ClearCreateInputs();
                return Task.CompletedTask;
            });
        }

        public ObservableCollection<SelfUseSheetJobDto> Jobs { get; }
        public ObservableCollection<RawMaterialInventoryLotDto> SourceLots { get; }
        public ObservableCollection<PartnerDto> Vendors { get; }
        public ObservableCollection<SelfUseSheetOption> PurposeOptions { get; }
        public ObservableCollection<SelfUseSheetOption> ExecutionOptions { get; }
        public ObservableCollection<SelfUseSheetOption> StatusOptions { get; }
        public ObservableCollection<SelfUseSheetOption> PurposeFilterOptions { get; }
        public AsyncRelayCommand RefreshCommand { get; }
        public AsyncRelayCommand CreateCommand { get; }
        public AsyncRelayCommand StartCommand { get; }
        public AsyncRelayCommand CompleteCommand { get; }
        public AsyncRelayCommand CancelCommand { get; }
        public AsyncRelayCommand ClearCommand { get; }

        public SelfUseSheetJobDto? SelectedJob
        {
            get => _selectedJob;
            set
            {
                if (!SetProperty(ref _selectedJob, value))
                {
                    return;
                }
                if (value != null)
                {
                    foreach (var allocation in value.Allocations)
                    {
                        allocation.ActualConsumedQty ??= allocation.PlannedQty;
                    }
                    ProducedQty = value.ProducedQty ?? value.PlannedOutputQty;
                    ScrapQty = value.ScrapQty ?? 0;
                    ActualProcessingFee = value.ActualProcessingFee ?? value.ExpectedProcessingFee;
                    CompletionMemo = value.Memo ?? string.Empty;
                    CancellationReason = string.Empty;
                }
                RaiseActionCanExecuteChanged();
            }
        }

        public string SearchKeyword { get => _searchKeyword; set => SetProperty(ref _searchKeyword, value); }
        public SelfUseSheetOption? SelectedStatusFilter { get => _selectedStatusFilter; set => SetProperty(ref _selectedStatusFilter, value); }
        public SelfUseSheetOption? SelectedPurposeFilter { get => _selectedPurposeFilter; set => SetProperty(ref _selectedPurposeFilter, value); }
        public RawMaterialInventoryLotDto? SelectedSourceLot
        {
            get => _selectedSourceLot;
            set
            {
                if (SetProperty(ref _selectedSourceLot, value))
                {
                    RecalculatePlannedOutputQty();
                }
            }
        }
        public PartnerDto? SelectedVendor { get => _selectedVendor; set => SetProperty(ref _selectedVendor, value); }
        public SelfUseSheetOption? SelectedPurpose { get => _selectedPurpose; set => SetProperty(ref _selectedPurpose, value); }
        public SelfUseSheetOption? SelectedExecution { get => _selectedExecution; set => SetProperty(ref _selectedExecution, value); }
        public decimal PlannedInputQty
        {
            get => _plannedInputQty;
            set
            {
                if (SetProperty(ref _plannedInputQty, value))
                {
                    RecalculatePlannedOutputQty();
                }
            }
        }
        public decimal CutWidthMm
        {
            get => _cutWidthMm;
            set
            {
                if (SetProperty(ref _cutWidthMm, value))
                {
                    RecalculatePlannedOutputQty();
                }
            }
        }
        public decimal CutLengthMm
        {
            get => _cutLengthMm;
            set
            {
                if (SetProperty(ref _cutLengthMm, value))
                {
                    RecalculatePlannedOutputQty();
                }
            }
        }
        public long PlannedOutputQty { get => _plannedOutputQty; set => SetProperty(ref _plannedOutputQty, value); }
        public decimal ExpectedProcessingFee { get => _expectedProcessingFee; set => SetProperty(ref _expectedProcessingFee, value); }
        public string Memo { get => _memo; set => SetProperty(ref _memo, value); }
        public long ProducedQty { get => _producedQty; set => SetProperty(ref _producedQty, value); }
        public long ScrapQty { get => _scrapQty; set => SetProperty(ref _scrapQty, value); }
        public decimal ActualProcessingFee { get => _actualProcessingFee; set => SetProperty(ref _actualProcessingFee, value); }
        public string CompletionMemo { get => _completionMemo; set => SetProperty(ref _completionMemo, value); }
        public string CancellationReason { get => _cancellationReason; set => SetProperty(ref _cancellationReason, value); }

        public async Task InitializeAsync()
        {
            await LoadMastersAsync();
            await LoadJobsAsync();
        }

        private async Task LoadMastersAsync()
        {
            var sourceLots = new List<RawMaterialInventoryLotDto>();
            var lotPage = 1;
            var fetchedLotCount = 0;
            while (true)
            {
                var lotsResult = await _apiClient.GetAsync<RawMaterialInventoryLotListDto>(
                    $"{ApiRoutes.RawMaterialInventoryLots}?page={lotPage}&size=200");
                if (!lotsResult.Success || lotsResult.Data == null)
                {
                    _messageService.ShowError(lotsResult.Message ?? "원자재 LOT 후보 조회 중 오류가 발생했습니다.");
                    break;
                }
                sourceLots.AddRange(lotsResult.Data.Items);
                fetchedLotCount += lotsResult.Data.Items.Count;
                if (fetchedLotCount >= lotsResult.Data.Total || lotsResult.Data.Items.Count == 0)
                {
                    break;
                }
                lotPage++;
            }
            SourceLots.Clear();
            foreach (var lot in sourceLots
                .Where(item =>
                    item.CurrentQty > 0 &&
                    item.LocationType != "OUTSOURCE_VENDOR" &&
                    string.Equals(item.Uom, "M", StringComparison.OrdinalIgnoreCase))
                .OrderBy(item => item.MaterialName)
                .ThenBy(item => item.LotNo))
            {
                SourceLots.Add(lot);
            }

            var vendors = new List<PartnerDto>();
            var vendorPage = 1;
            var fetchedVendorCount = 0;
            while (true)
            {
                var vendorResult = await _apiClient.GetAsync<PartnerListDto>(
                    $"{ApiRoutes.Partners}?page={vendorPage}&size=100&partner_type=VENDOR&is_active=true");
                if (!vendorResult.Success || vendorResult.Data == null)
                {
                    _messageService.ShowError(vendorResult.Message ?? "외주처 후보 조회 중 오류가 발생했습니다.");
                    break;
                }
                vendors.AddRange(vendorResult.Data.Items);
                fetchedVendorCount += vendorResult.Data.Items.Count;
                if (fetchedVendorCount >= vendorResult.Data.Total || vendorResult.Data.Items.Count == 0)
                {
                    break;
                }
                vendorPage++;
            }
            Vendors.Clear();
            foreach (var vendor in vendors.Where(item => item.IsActive).OrderBy(item => item.Name))
            {
                Vendors.Add(vendor);
            }
        }

        private async Task LoadJobsAsync()
        {
            var query = new List<string> { "page=1", "size=200" };
            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }
            if (!string.IsNullOrWhiteSpace(SelectedStatusFilter?.Code))
            {
                query.Add($"status={SelectedStatusFilter.Code}");
            }
            if (!string.IsNullOrWhiteSpace(SelectedPurposeFilter?.Code))
            {
                query.Add($"purpose_type={SelectedPurposeFilter.Code}");
            }
            var result = await _apiClient.GetAsync<SelfUseSheetJobListDto>(
                $"{ApiRoutes.SelfUseSheetJobs}?{string.Join("&", query)}");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 작업 조회 중 오류가 발생했습니다.");
                return;
            }
            var selectedId = SelectedJob?.SelfUseSheetJobId;
            Jobs.Clear();
            foreach (var item in result.Data.Items)
            {
                Jobs.Add(item);
            }
            SelectedJob = selectedId.HasValue
                ? Jobs.FirstOrDefault(item => item.SelfUseSheetJobId == selectedId.Value)
                : Jobs.FirstOrDefault();
        }

        private async Task CreateAsync()
        {
            if (SelectedSourceLot == null || SelectedPurpose == null || SelectedExecution == null)
            {
                _messageService.ShowWarning("사용 목적, 가공 구분 및 원자재 LOT를 선택하세요.");
                return;
            }
            if (PlannedInputQty <= 0 || PlannedInputQty > SelectedSourceLot.CurrentQty)
            {
                _messageService.ShowWarning("투입 예정수량은 0보다 크고 선택 LOT의 현재고 이하여야 합니다.");
                return;
            }
            if (!string.Equals(SelectedSourceLot.Uom, "M", StringComparison.OrdinalIgnoreCase))
            {
                _messageService.ShowWarning("자가사용 시트지는 수량 단위가 M인 원자재 LOT만 등록할 수 있습니다.");
                return;
            }
            if (!HasValidWholeMillimeterDimensions())
            {
                _messageService.ShowWarning("재단 폭과 길이는 0보다 큰 정수 mm로 입력하세요.");
                return;
            }
            if (CutWidthMm <= 0 || CutLengthMm <= 0 || PlannedOutputQty <= 0)
            {
                _messageService.ShowWarning("투입 예정수량과 재단 규격을 확인하세요.");
                return;
            }
            if (SelectedExecution.Code == "OUTSOURCE" && SelectedVendor == null)
            {
                _messageService.ShowWarning("외주 재단은 외주처를 선택해야 합니다.");
                return;
            }
            if (SelectedPurpose.Code == "OTHER" && string.IsNullOrWhiteSpace(Memo))
            {
                _messageService.ShowWarning("기타 목적은 작업 메모를 반드시 입력하세요.");
                return;
            }
            var request = new SelfUseSheetJobCreateRequest
            {
                PurposeType = SelectedPurpose.Code,
                ExecutionType = SelectedExecution.Code,
                PartnerId = SelectedExecution.Code == "OUTSOURCE" ? SelectedVendor?.PartnerId : null,
                CutWidthMm = CutWidthMm,
                CutLengthMm = CutLengthMm,
                PlannedOutputQty = PlannedOutputQty,
                ExpectedProcessingFee = ExpectedProcessingFee,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim(),
                Allocations = new List<SelfUseSheetAllocationCreateRequest>
                {
                    new()
                    {
                        RawMaterialInventoryLotId = SelectedSourceLot.RawMaterialInventoryLotId,
                        PlannedQty = PlannedInputQty
                    }
                }
            };
            var result = await _apiClient.PostAsync<SelfUseSheetJobCreateRequest, SelfUseSheetJobDto>(
                ApiRoutes.SelfUseSheetJobs,
                request);
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 작업 등록 중 오류가 발생했습니다.");
                return;
            }
            ClearCreateInputs();
            await LoadMastersAsync();
            await LoadJobsAsync();
            SelectedJob = Jobs.FirstOrDefault(item => item.SelfUseSheetJobId == result.Data.SelfUseSheetJobId);
            _messageService.ShowInfo("자가사용 시트지 작업을 임시저장했습니다.");
        }

        private async Task StartAsync()
        {
            if (SelectedJob == null || !_messageService.Confirm(
                "가공출고/작업시작 처리하면 원자재 재고가 확보됩니다. 계속하시겠습니까?"))
            {
                return;
            }
            var result = await _apiClient.PostAsync<SelfUseSheetJobStartRequest, SelfUseSheetJobDto>(
                $"{ApiRoutes.SelfUseSheetJobs}/{SelectedJob.SelfUseSheetJobId}/start",
                new SelfUseSheetJobStartRequest { ExpectedVersion = SelectedJob.Version });
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "가공출고 처리 중 오류가 발생했습니다.");
                return;
            }
            await LoadMastersAsync();
            await LoadJobsAsync();
            _messageService.ShowInfo("가공출고/작업시작 처리했습니다.");
        }

        private async Task CompleteAsync()
        {
            if (SelectedJob == null || ProducedQty <= 0 || ActualProcessingFee < 0)
            {
                _messageService.ShowWarning("정상 생산수량과 실제 가공비를 확인하세요.");
                return;
            }
            if (SelectedJob.Allocations.Any(item => !item.ActualConsumedQty.HasValue ||
                item.ActualConsumedQty <= 0 ||
                item.ActualConsumedQty.Value + item.ReturnedQty != item.PlannedQty))
            {
                _messageService.ShowWarning("각 원자재 LOT의 실제투입 + 반환수량이 투입예정수량과 같아야 합니다.");
                return;
            }
            if (!_messageService.Confirm("완료 처리하면 자가사용 시트지 LOT가 생성됩니다. 계속하시겠습니까?"))
            {
                return;
            }
            var request = new SelfUseSheetJobCompleteRequest
            {
                ExpectedVersion = SelectedJob.Version,
                ProducedQty = ProducedQty,
                ScrapQty = ScrapQty,
                ActualProcessingFee = ActualProcessingFee,
                Memo = string.IsNullOrWhiteSpace(CompletionMemo) ? null : CompletionMemo.Trim(),
                Allocations = SelectedJob.Allocations.Select(item => new SelfUseSheetAllocationCompleteRequest
                {
                    AllocationId = item.AllocationId,
                    ActualConsumedQty = item.ActualConsumedQty!.Value,
                    ReturnedQty = item.ReturnedQty
                }).ToList()
            };
            var result = await _apiClient.PostAsync<SelfUseSheetJobCompleteRequest, SelfUseSheetJobDto>(
                $"{ApiRoutes.SelfUseSheetJobs}/{SelectedJob.SelfUseSheetJobId}/complete",
                request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "재단 완료 처리 중 오류가 발생했습니다.");
                return;
            }
            await LoadMastersAsync();
            await LoadJobsAsync();
            _messageService.ShowInfo("재단 완료 및 자가사용 시트지 재고 생성을 완료했습니다.");
        }

        private async Task CancelAsync()
        {
            if (SelectedJob == null || string.IsNullOrWhiteSpace(CancellationReason))
            {
                _messageService.ShowWarning("취소 사유를 입력하세요.");
                return;
            }
            if (!_messageService.Confirm("작업을 취소하고 관련 원자재 수불을 복원하시겠습니까?"))
            {
                return;
            }
            var result = await _apiClient.PostAsync<SelfUseSheetJobCancelRequest, SelfUseSheetJobDto>(
                $"{ApiRoutes.SelfUseSheetJobs}/{SelectedJob.SelfUseSheetJobId}/cancel",
                new SelfUseSheetJobCancelRequest
                {
                    ExpectedVersion = SelectedJob.Version,
                    Reason = CancellationReason.Trim()
                });
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 작업 취소 중 오류가 발생했습니다.");
                return;
            }
            await LoadMastersAsync();
            await LoadJobsAsync();
            _messageService.ShowInfo("작업을 취소했습니다.");
        }

        private void ClearCreateInputs()
        {
            SelectedSourceLot = null;
            SelectedVendor = null;
            SelectedPurpose = PurposeOptions[0];
            SelectedExecution = ExecutionOptions[1];
            PlannedInputQty = 0;
            CutWidthMm = 0;
            CutLengthMm = 0;
            PlannedOutputQty = 0;
            ExpectedProcessingFee = 0;
            Memo = string.Empty;
        }

        private bool HasValidWholeMillimeterDimensions()
        {
            return CutWidthMm > 0 &&
                CutLengthMm > 0 &&
                CutWidthMm <= int.MaxValue &&
                CutLengthMm <= int.MaxValue &&
                CutWidthMm == decimal.Truncate(CutWidthMm) &&
                CutLengthMm == decimal.Truncate(CutLengthMm);
        }

        private void RecalculatePlannedOutputQty()
        {
            if (SelectedSourceLot == null ||
                !string.Equals(SelectedSourceLot.Uom, "M", StringComparison.OrdinalIgnoreCase) ||
                PlannedInputQty <= 0 ||
                !HasValidWholeMillimeterDimensions())
            {
                PlannedOutputQty = 0;
                return;
            }

            PlannedOutputQty = SheetQtyCalculator.Calculate(
                PlannedInputQty,
                decimal.ToInt32(CutLengthMm),
                decimal.ToInt32(CutWidthMm));
        }

        private void RaiseActionCanExecuteChanged()
        {
            StartCommand.RaiseCanExecuteChanged();
            CompleteCommand.RaiseCanExecuteChanged();
            CancelCommand.RaiseCanExecuteChanged();
        }
    }
}
