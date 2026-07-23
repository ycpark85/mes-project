using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.RawMaterials.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.RawMaterials.ViewModels
{
    public class SelfUseSheetInventoryPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private SelfUseSheetInventoryLotDto? _selectedLot;
        private SelfUseSheetInventoryLocationRow? _selectedLocationRow;
        private SelfUseSheetMovementDto? _selectedMovement;
        private SelfUseSheetOption? _selectedStatus;
        private SelfUseSheetOption? _selectedUsePurpose;
        private string _searchKeyword = string.Empty;
        private long _useQty;
        private string _useMemo = string.Empty;
        private string _reverseReason = string.Empty;
        private int _lotCount;
        private long _totalInitialQty;
        private long _totalUsedQty;
        private long _totalCurrentQty;
        private decimal _inventoryAmount;
        private SelfUseSheetInventoryLocationDto? _selectedUseLocation;
        private SelfUseSheetInventoryLocationDto? _selectedTransferFromLocation;
        private RawMaterialLocationDto? _selectedTransferToLocation;
        private long _transferQty;
        private string _transferReason = string.Empty;
        private string _movementSearchKeyword = string.Empty;
        private SelfUseSheetOption? _selectedMovementType;
        private DateTime? _movementDateFrom;
        private DateTime? _movementDateTo;
        private int _movementPage = 1;
        private int _movementTotal;
        private const int MovementPageSize = 200;

        public SelfUseSheetInventoryPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            Lots = new ObservableCollection<SelfUseSheetInventoryLotDto>();
            LocationRows = new ObservableCollection<SelfUseSheetInventoryLocationRow>();
            Movements = new ObservableCollection<SelfUseSheetMovementDto>();
            ActiveLocations = new ObservableCollection<RawMaterialLocationDto>();
            StatusOptions = new ObservableCollection<SelfUseSheetOption>
            {
                new(string.Empty, "전체"),
                new("AVAILABLE", "사용가능"),
                new("DEPLETED", "소진"),
                new("CANCELED", "취소")
            };
            PurposeOptions = new ObservableCollection<SelfUseSheetOption>
            {
                new("PRINT_SETUP", "인쇄 초기 셋팅"),
                new("SAMPLE", "샘플 제작"),
                new("TEST_RND", "시험/개발"),
                new("OTHER", "기타")
            };
            MovementTypeOptions = new ObservableCollection<SelfUseSheetOption>
            {
                new(string.Empty, "전체"),
                new("PRODUCE_IN", "재단완료 입고"),
                new("USE_OUT", "사용"),
                new("USE_REVERSE", "사용취소"),
                new("TRANSFER_OUT", "위치이동 출고"),
                new("TRANSFER_IN", "위치이동 입고"),
                new("WORK_USE_OUT", "외주작업 투입"),
                new("WORK_USE_REVERSE", "외주작업 투입취소"),
                new("CANCEL_OUT", "완료취소")
            };
            _selectedStatus = StatusOptions[0];
            _selectedUsePurpose = PurposeOptions[0];
            _selectedMovementType = MovementTypeOptions[0];
            RefreshCommand = new AsyncRelayCommand(LoadLotsAsync);
            RefreshMovementsCommand = new AsyncRelayCommand(RefreshMovementsAsync);
            PreviousMovementPageCommand = new AsyncRelayCommand(
                () => ChangeMovementPageAsync(-1),
                () => MovementPage > 1);
            NextMovementPageCommand = new AsyncRelayCommand(
                () => ChangeMovementPageAsync(1),
                () => MovementPage * MovementPageSize < MovementTotal);
            UseCommand = new AsyncRelayCommand(
                UseAsync,
                () => SelectedLot != null
                    && SelectedLot.Status == "AVAILABLE"
                    && SelectedLot.CurrentQty > 0
                    && SelectedUseLocation != null);
            ReverseCommand = new AsyncRelayCommand(
                ReverseAsync,
                () => SelectedMovement?.MovementType == "USE_OUT");
            TransferCommand = new AsyncRelayCommand(
                TransferAsync,
                () => SelectedLot != null && SelectedTransferFromLocation != null && SelectedTransferToLocation != null);
        }

        public ObservableCollection<SelfUseSheetInventoryLotDto> Lots { get; }
        public ObservableCollection<SelfUseSheetInventoryLocationRow> LocationRows { get; }
        public ObservableCollection<SelfUseSheetMovementDto> Movements { get; }
        public ObservableCollection<RawMaterialLocationDto> ActiveLocations { get; }
        public ObservableCollection<SelfUseSheetOption> StatusOptions { get; }
        public ObservableCollection<SelfUseSheetOption> PurposeOptions { get; }
        public ObservableCollection<SelfUseSheetOption> MovementTypeOptions { get; }
        public AsyncRelayCommand RefreshCommand { get; }
        public AsyncRelayCommand RefreshMovementsCommand { get; }
        public AsyncRelayCommand UseCommand { get; }
        public AsyncRelayCommand ReverseCommand { get; }
        public AsyncRelayCommand TransferCommand { get; }
        public AsyncRelayCommand PreviousMovementPageCommand { get; }
        public AsyncRelayCommand NextMovementPageCommand { get; }

        public SelfUseSheetInventoryLotDto? SelectedLot
        {
            get => _selectedLot;
            set
            {
                if (!SetProperty(ref _selectedLot, value))
                {
                    return;
                }
                UseQty = 0;
                UseMemo = string.Empty;
                ReverseReason = string.Empty;
                SelectedMovement = null;
                SelectedUseLocation = value?.Locations.FirstOrDefault();
                SelectedTransferFromLocation = value?.Locations.FirstOrDefault();
                if (_selectedLocationRow?.Lot.SelfUseSheetInventoryLotId != value?.SelfUseSheetInventoryLotId)
                {
                    SelectLocationRow(value);
                }
                UseCommand.RaiseCanExecuteChanged();
                TransferCommand.RaiseCanExecuteChanged();
            }
        }

        public SelfUseSheetInventoryLocationRow? SelectedLocationRow
        {
            get => _selectedLocationRow;
            set
            {
                if (!SetProperty(ref _selectedLocationRow, value) || value == null)
                {
                    return;
                }
                SelectedLot = value.Lot;
                SelectedTransferFromLocation = value.Location;
            }
        }

        public SelfUseSheetMovementDto? SelectedMovement
        {
            get => _selectedMovement;
            set
            {
                if (SetProperty(ref _selectedMovement, value))
                {
                    ReverseCommand.RaiseCanExecuteChanged();
                }
            }
        }

        public string SearchKeyword { get => _searchKeyword; set => SetProperty(ref _searchKeyword, value); }
        public SelfUseSheetOption? SelectedStatus { get => _selectedStatus; set => SetProperty(ref _selectedStatus, value); }
        public SelfUseSheetOption? SelectedUsePurpose { get => _selectedUsePurpose; set => SetProperty(ref _selectedUsePurpose, value); }
        public long UseQty { get => _useQty; set => SetProperty(ref _useQty, value); }
        public string UseMemo { get => _useMemo; set => SetProperty(ref _useMemo, value); }
        public string ReverseReason { get => _reverseReason; set => SetProperty(ref _reverseReason, value); }
        public int LotCount { get => _lotCount; set => SetProperty(ref _lotCount, value); }
        public long TotalInitialQty { get => _totalInitialQty; set => SetProperty(ref _totalInitialQty, value); }
        public long TotalUsedQty { get => _totalUsedQty; set => SetProperty(ref _totalUsedQty, value); }
        public long TotalCurrentQty { get => _totalCurrentQty; set => SetProperty(ref _totalCurrentQty, value); }
        public decimal InventoryAmount { get => _inventoryAmount; set => SetProperty(ref _inventoryAmount, value); }
        public SelfUseSheetInventoryLocationDto? SelectedUseLocation
        {
            get => _selectedUseLocation;
            set
            {
                if (SetProperty(ref _selectedUseLocation, value))
                {
                    UseCommand.RaiseCanExecuteChanged();
                }
            }
        }
        public SelfUseSheetInventoryLocationDto? SelectedTransferFromLocation
        {
            get => _selectedTransferFromLocation;
            set { if (SetProperty(ref _selectedTransferFromLocation, value)) TransferCommand.RaiseCanExecuteChanged(); }
        }
        public RawMaterialLocationDto? SelectedTransferToLocation
        {
            get => _selectedTransferToLocation;
            set { if (SetProperty(ref _selectedTransferToLocation, value)) TransferCommand.RaiseCanExecuteChanged(); }
        }
        public long TransferQty { get => _transferQty; set => SetProperty(ref _transferQty, value); }
        public string TransferReason { get => _transferReason; set => SetProperty(ref _transferReason, value); }
        public string MovementSearchKeyword { get => _movementSearchKeyword; set => SetProperty(ref _movementSearchKeyword, value); }
        public SelfUseSheetOption? SelectedMovementType { get => _selectedMovementType; set => SetProperty(ref _selectedMovementType, value); }
        public DateTime? MovementDateFrom { get => _movementDateFrom; set => SetProperty(ref _movementDateFrom, value); }
        public DateTime? MovementDateTo { get => _movementDateTo; set => SetProperty(ref _movementDateTo, value); }
        public int MovementPage
        {
            get => _movementPage;
            set
            {
                if (SetProperty(ref _movementPage, value))
                {
                    OnPropertyChanged(nameof(MovementPageDisplay));
                    PreviousMovementPageCommand.RaiseCanExecuteChanged();
                    NextMovementPageCommand.RaiseCanExecuteChanged();
                }
            }
        }
        public int MovementTotal
        {
            get => _movementTotal;
            set
            {
                if (SetProperty(ref _movementTotal, value))
                {
                    OnPropertyChanged(nameof(MovementPageDisplay));
                    PreviousMovementPageCommand.RaiseCanExecuteChanged();
                    NextMovementPageCommand.RaiseCanExecuteChanged();
                }
            }
        }
        public string MovementPageDisplay => $"{MovementPage:N0} 페이지 / 총 {MovementTotal:N0}건";

        public async Task InitializeAsync()
        {
            await Task.WhenAll(LoadLocationsAsync(), LoadLotsAsync(), LoadMovementsAsync());
        }

        private async Task LoadLocationsAsync()
        {
            var result = await _apiClient.GetAsync<RawMaterialLocationListDto>($"{ApiRoutes.RawMaterialLocations}?page=1&size=200&is_active=true");
            ActiveLocations.Clear();
            if (result.Success && result.Data != null)
            {
                foreach (var item in result.Data.Items.Where(x => x.IsActive)) ActiveLocations.Add(item);
            }
        }

        private async Task LoadLotsAsync()
        {
            var query = new List<string> { "page=1", "size=200" };
            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }
            if (!string.IsNullOrWhiteSpace(SelectedStatus?.Code))
            {
                query.Add($"status={SelectedStatus.Code}");
            }
            var result = await _apiClient.GetAsync<SelfUseSheetInventoryListDto>(
                $"{ApiRoutes.SelfUseSheetInventory}?{string.Join("&", query)}");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 재고 조회 중 오류가 발생했습니다.");
                return;
            }
            var selectedId = SelectedLot?.SelfUseSheetInventoryLotId;
            var selectedLocationId = SelectedLocationRow?.Location?.RawMaterialLocationId;
            Lots.Clear();
            LocationRows.Clear();
            foreach (var item in result.Data.Items)
            {
                Lots.Add(item);
                if (item.Locations.Count == 0)
                {
                    LocationRows.Add(new SelfUseSheetInventoryLocationRow(item, null));
                    continue;
                }
                foreach (var location in item.Locations.OrderBy(x => x.LocationCode))
                {
                    LocationRows.Add(new SelfUseSheetInventoryLocationRow(item, location));
                }
            }
            LotCount = result.Data.Summary.LotCount;
            TotalInitialQty = result.Data.Summary.InitialQty;
            TotalUsedQty = result.Data.Summary.UsedQty;
            TotalCurrentQty = result.Data.Summary.CurrentQty;
            InventoryAmount = result.Data.Summary.InventoryAmount;
            SelectedLot = selectedId.HasValue
                ? Lots.FirstOrDefault(item => item.SelfUseSheetInventoryLotId == selectedId.Value)
                : Lots.FirstOrDefault();
            SelectLocationRow(SelectedLot, selectedLocationId);
        }

        private void SelectLocationRow(SelfUseSheetInventoryLotDto? lot, long? preferredLocationId = null)
        {
            var row = lot == null
                ? null
                : LocationRows.FirstOrDefault(x =>
                    x.Lot.SelfUseSheetInventoryLotId == lot.SelfUseSheetInventoryLotId
                    && (!preferredLocationId.HasValue
                        || x.Location?.RawMaterialLocationId == preferredLocationId.Value))
                  ?? LocationRows.FirstOrDefault(x =>
                      x.Lot.SelfUseSheetInventoryLotId == lot.SelfUseSheetInventoryLotId);
            if (SetProperty(ref _selectedLocationRow, row, nameof(SelectedLocationRow)))
            {
                SelectedTransferFromLocation = row?.Location;
            }
        }

        private async Task LoadMovementsAsync()
        {
            Movements.Clear();
            var query = new List<string>
            {
                $"page={MovementPage}",
                $"size={MovementPageSize}"
            };
            if (!string.IsNullOrWhiteSpace(MovementSearchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(MovementSearchKeyword.Trim())}");
            }
            if (!string.IsNullOrWhiteSpace(SelectedMovementType?.Code))
            {
                query.Add($"movement_type={Uri.EscapeDataString(SelectedMovementType.Code)}");
            }
            if (MovementDateFrom.HasValue)
            {
                query.Add($"date_from={MovementDateFrom.Value:yyyy-MM-dd}");
            }
            if (MovementDateTo.HasValue)
            {
                query.Add($"date_to={MovementDateTo.Value:yyyy-MM-dd}");
            }
            var result = await _apiClient.GetAsync<SelfUseSheetMovementListDto>(
                $"{ApiRoutes.SelfUseSheetMovements}?{string.Join("&", query)}");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 사용 이력 조회 중 오류가 발생했습니다.");
                return;
            }
            foreach (var item in result.Data.Items)
            {
                Movements.Add(item);
            }
            MovementTotal = result.Data.Total;
            MovementPage = result.Data.Page;
        }

        private async Task RefreshMovementsAsync()
        {
            MovementPage = 1;
            await LoadMovementsAsync();
        }

        private async Task ChangeMovementPageAsync(int delta)
        {
            var nextPage = MovementPage + delta;
            if (nextPage < 1 || (delta > 0 && MovementPage * MovementPageSize >= MovementTotal))
            {
                return;
            }
            MovementPage = nextPage;
            await LoadMovementsAsync();
        }

        private async Task UseAsync()
        {
            if (SelectedLot == null || SelectedUseLocation == null || SelectedUsePurpose == null
                || UseQty <= 0 || UseQty > SelectedUseLocation.CurrentQty)
            {
                _messageService.ShowWarning("사용 위치와 목적을 선택하고, 해당 위치의 사용가능 수량 이내로 입력하세요.");
                return;
            }
            if (SelectedUsePurpose.Code == "OTHER" && string.IsNullOrWhiteSpace(UseMemo))
            {
                _messageService.ShowWarning("기타 목적은 메모를 반드시 입력하세요.");
                return;
            }
            if (!_messageService.Confirm($"선택한 시트지에서 {UseQty:N0}매를 사용 처리하시겠습니까?"))
            {
                return;
            }
            var result = await _apiClient.PostAsync<SelfUseSheetUseRequest, SelfUseSheetInventoryLotDto>(
                $"{ApiRoutes.SelfUseSheetInventory}/{SelectedLot.SelfUseSheetInventoryLotId}/use",
                new SelfUseSheetUseRequest
                {
                    ExpectedVersion = SelectedLot.Version,
                    PurposeType = SelectedUsePurpose.Code,
                    Qty = UseQty,
                    RawMaterialLocationId = SelectedUseLocation?.RawMaterialLocationId,
                    Memo = string.IsNullOrWhiteSpace(UseMemo) ? null : UseMemo.Trim()
                });
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 사용 처리 중 오류가 발생했습니다.");
                return;
            }
            await LoadLotsAsync();
            await LoadMovementsAsync();
            _messageService.ShowInfo("자가사용 시트지 재고를 차감했습니다.");
        }

        private async Task ReverseAsync()
        {
            if (SelectedMovement == null || string.IsNullOrWhiteSpace(ReverseReason))
            {
                _messageService.ShowWarning("취소할 사용 이력과 취소 사유를 입력하세요.");
                return;
            }
            if (!_messageService.Confirm("선택한 사용 이력을 취소하고 재고를 복원하시겠습니까?"))
            {
                return;
            }
            var result = await _apiClient.PostAsync<SelfUseSheetUseReverseRequest, SelfUseSheetInventoryLotDto>(
                $"{ApiRoutes.SelfUseSheetMovements}/{SelectedMovement.SelfUseSheetInventoryMovementId}/reverse",
                new SelfUseSheetUseReverseRequest
                {
                    ExpectedVersion = SelectedMovement.InventoryLotVersion,
                    Reason = ReverseReason.Trim()
                });
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 사용 취소 중 오류가 발생했습니다.");
                return;
            }
            await LoadLotsAsync();
            await LoadMovementsAsync();
            _messageService.ShowInfo("사용 이력을 취소하고 재고를 복원했습니다.");
        }

        private async Task TransferAsync()
        {
            if (SelectedLot == null || SelectedTransferFromLocation == null || SelectedTransferToLocation == null
                || TransferQty <= 0 || TransferQty > SelectedTransferFromLocation.CurrentQty
                || string.IsNullOrWhiteSpace(TransferReason))
            {
                _messageService.ShowWarning("출발 위치, 도착 위치, 이동수량 및 이동사유를 확인하세요.");
                return;
            }
            if (SelectedTransferFromLocation.RawMaterialLocationId == SelectedTransferToLocation.RawMaterialLocationId)
            {
                _messageService.ShowWarning("출발 위치와 도착 위치는 달라야 합니다.");
                return;
            }
            var result = await _apiClient.PostAsync<SelfUseSheetTransferRequest, SelfUseSheetInventoryLotDto>(
                $"{ApiRoutes.SelfUseSheetInventory}/{SelectedLot.SelfUseSheetInventoryLotId}/transfer",
                new SelfUseSheetTransferRequest
                {
                    ExpectedVersion = SelectedLot.Version,
                    FromLocationId = SelectedTransferFromLocation.RawMaterialLocationId,
                    ToLocationId = SelectedTransferToLocation.RawMaterialLocationId,
                    Qty = TransferQty,
                    Reason = TransferReason.Trim()
                });
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "자가사용 시트지 위치이동 중 오류가 발생했습니다.");
                return;
            }
            TransferQty = 0;
            TransferReason = string.Empty;
            await LoadLotsAsync();
            await LoadMovementsAsync();
            _messageService.ShowInfo("자가사용 시트지 위치이동을 완료했습니다.");
        }
    }

    public sealed class SelfUseSheetInventoryLocationRow
    {
        public SelfUseSheetInventoryLocationRow(
            SelfUseSheetInventoryLotDto lot,
            SelfUseSheetInventoryLocationDto? location)
        {
            Lot = lot;
            Location = location;
        }

        public SelfUseSheetInventoryLotDto Lot { get; }
        public SelfUseSheetInventoryLocationDto? Location { get; }
        public string LocationName => Location?.LocationName ?? "위치 없음";
        public long LocationQty => Location?.CurrentQty ?? 0;
    }
}
