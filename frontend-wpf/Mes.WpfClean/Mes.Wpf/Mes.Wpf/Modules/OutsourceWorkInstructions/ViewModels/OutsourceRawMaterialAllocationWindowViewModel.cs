using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using Mes.Wpf.Modules.RawMaterials.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels
{
    public sealed class OutsourceRawMaterialAllocationWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly Func<long, decimal> _reservedQtyProvider;
        private readonly Dictionary<long, decimal> _currentDraftQtyByLotId;
        private readonly Dictionary<long, OutsourceWorkInstructionRawMaterialAllocationEditModel> _allocationByLotId;
        private readonly HashSet<long> _loadedLotIds = new();
        private readonly bool _currentAllocationsAreConsumed;
        private readonly long? _initialMaterialId;
        private readonly long? _initialLocationId;
        private RawMaterialDto? _selectedMaterial;
        private RawMaterialLocationDto? _selectedLocation;
        private RawMaterialAllocationLotRowModel? _selectedLotRow;
        private OutsourceWorkInstructionRawMaterialAllocationEditModel? _selectedBasketAllocation;
        private decimal? _allocationInputQty;
        private bool _isLoading;

        public OutsourceRawMaterialAllocationWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            decimal requiredQty,
            IEnumerable<OutsourceWorkInstructionRawMaterialAllocationEditModel> currentAllocations,
            Func<long, decimal> reservedQtyProvider,
            bool currentAllocationsAreConsumed = false)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _reservedQtyProvider = reservedQtyProvider;
            _currentAllocationsAreConsumed = currentAllocationsAreConsumed;
            RequiredQty = requiredQty;
            var firstAllocation = currentAllocations.FirstOrDefault();
            _initialMaterialId = firstAllocation?.RawMaterialId;
            _initialLocationId = firstAllocation?.RawMaterialLocationId;
            _currentDraftQtyByLotId = currentAllocations
                .GroupBy(x => x.RawMaterialInventoryLotId)
                .ToDictionary(x => x.Key, x => x.Sum(y => y.Qty));
            _allocationByLotId = new Dictionary<long, OutsourceWorkInstructionRawMaterialAllocationEditModel>();

            Materials = new ObservableCollection<RawMaterialDto>();
            Locations = new ObservableCollection<RawMaterialLocationDto>();
            LotRows = new ObservableCollection<RawMaterialAllocationLotRowModel>();
            AllocationBasket = new ObservableCollection<OutsourceWorkInstructionRawMaterialAllocationEditModel>();
            foreach (var allocation in currentAllocations
                         .GroupBy(x => x.RawMaterialInventoryLotId)
                         .Select(x => CloneAllocation(x.First(), x.Sum(y => y.Qty))))
            {
                _allocationByLotId.Add(allocation.RawMaterialInventoryLotId, allocation);
                AllocationBasket.Add(allocation);
            }
            SelectedBasketAllocation = AllocationBasket.FirstOrDefault();
            AppliedAllocations = new List<OutsourceWorkInstructionRawMaterialAllocationEditModel>();

            SearchLotsCommand = new AsyncRelayCommand(SearchLotsAsync);
            AssignSelectedLotCommand = new RelayCommand(AssignSelectedLot);
            ClearSelectedLotCommand = new RelayCommand(ClearSelectedLot);
            RemoveBasketAllocationCommand = new RelayCommand(RemoveBasketAllocation);
            ApplyCommand = new RelayCommand(Apply);
            CancelCommand = new RelayCommand(Cancel);
        }

        public Window? OwnerWindow { get; set; }

        public ObservableCollection<RawMaterialDto> Materials { get; }
        public ObservableCollection<RawMaterialLocationDto> Locations { get; }
        public ObservableCollection<RawMaterialAllocationLotRowModel> LotRows { get; }
        public ObservableCollection<OutsourceWorkInstructionRawMaterialAllocationEditModel> AllocationBasket { get; }
        public List<OutsourceWorkInstructionRawMaterialAllocationEditModel> AppliedAllocations { get; }

        public AsyncRelayCommand SearchLotsCommand { get; }
        public RelayCommand AssignSelectedLotCommand { get; }
        public RelayCommand ClearSelectedLotCommand { get; }
        public RelayCommand RemoveBasketAllocationCommand { get; }
        public RelayCommand ApplyCommand { get; }
        public RelayCommand CancelCommand { get; }

        public decimal RequiredQty { get; }

        public decimal TotalAllocationQty => AllocationBasket.Sum(x => x.Qty);
        public decimal RemainingQty => RequiredQty - TotalAllocationQty;
        public decimal SelectedLotMaxAllocationQty
        {
            get
            {
                if (SelectedLotRow == null)
                {
                    return 0m;
                }

                var otherTotal = TotalAllocationQty - SelectedLotRow.AllocationQty;
                var remainingIncludingSelected = RequiredQty - otherTotal;
                return Math.Max(0m, Math.Min(SelectedLotRow.AvailableQty, remainingIncludingSelected));
            }
        }

        public RawMaterialDto? SelectedMaterial
        {
            get => _selectedMaterial;
            set => SetProperty(ref _selectedMaterial, value);
        }

        public RawMaterialLocationDto? SelectedLocation
        {
            get => _selectedLocation;
            set => SetProperty(ref _selectedLocation, value);
        }

        public RawMaterialAllocationLotRowModel? SelectedLotRow
        {
            get => _selectedLotRow;
            set
            {
                if (SetProperty(ref _selectedLotRow, value))
                {
                    AllocationInputQty = ResolveDefaultAllocationQty(value);
                    OnPropertyChanged(nameof(SelectedLotMaxAllocationQty));
                }
            }
        }

        public OutsourceWorkInstructionRawMaterialAllocationEditModel? SelectedBasketAllocation
        {
            get => _selectedBasketAllocation;
            set => SetProperty(ref _selectedBasketAllocation, value);
        }

        public decimal? AllocationInputQty
        {
            get => _allocationInputQty;
            set => SetProperty(ref _allocationInputQty, value);
        }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public async Task InitializeAsync()
        {
            IsLoading = true;

            try
            {
                var materialResult = await _apiClient.GetAsync<RawMaterialListDto>(
                    $"{ApiRoutes.RawMaterials}?page=1&size=200&is_active=true");
                var locationResult = await _apiClient.GetAsync<RawMaterialLocationListDto>(
                    $"{ApiRoutes.RawMaterialLocations}?page=1&size=200&is_active=true");

                Materials.Clear();
                Locations.Clear();

                if (materialResult.Success && materialResult.Data != null)
                {
                    foreach (var material in materialResult.Data.Items)
                    {
                        Materials.Add(material);
                    }
                }

                if (locationResult.Success && locationResult.Data != null)
                {
                    foreach (var location in locationResult.Data.Items)
                    {
                        Locations.Add(location);
                    }
                }

                SelectedMaterial = _initialMaterialId.HasValue
                    ? Materials.FirstOrDefault(x => x.RawMaterialId == _initialMaterialId.Value) ?? Materials.FirstOrDefault()
                    : Materials.FirstOrDefault();
                SelectedLocation = _initialLocationId.HasValue
                    ? Locations.FirstOrDefault(x => x.RawMaterialLocationId == _initialLocationId.Value) ?? Locations.FirstOrDefault()
                    : Locations.FirstOrDefault();

                await SearchLotsAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task SearchLotsAsync()
        {
            if (SelectedMaterial == null || SelectedLocation == null)
            {
                LotRows.Clear();
                return;
            }

            IsLoading = true;

            try
            {
                var url = $"{ApiRoutes.RawMaterialInventoryLots}?page=1&size=200" +
                    $"&raw_material_id={SelectedMaterial.RawMaterialId}" +
                    $"&location_id={SelectedLocation.RawMaterialLocationId}";
                var result = await _apiClient.GetAsync<RawMaterialInventoryLotListDto>(url);

                LotRows.Clear();

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "원자재 LOT 조회 중 오류가 발생했습니다.");
                    return;
                }

                foreach (var lot in result.Data.Items)
                {
                    var originalDraftQty = _currentDraftQtyByLotId.TryGetValue(
                        lot.RawMaterialInventoryLotId,
                        out var draftQty)
                        ? draftQty
                        : 0m;
                    var basketQty = _allocationByLotId.TryGetValue(
                        lot.RawMaterialInventoryLotId,
                        out var basketAllocation)
                        ? basketAllocation.Qty
                        : 0m;
                    var otherReservedQty = Math.Max(
                        0m,
                        _reservedQtyProvider(lot.RawMaterialInventoryLotId) - originalDraftQty);
                    var row = RawMaterialAllocationLotRowModel.FromDto(
                        lot,
                        otherReservedQty,
                        basketQty,
                        _currentAllocationsAreConsumed ? originalDraftQty : 0m);
                    LotRows.Add(row);
                    _loadedLotIds.Add(lot.RawMaterialInventoryLotId);
                    if (basketAllocation != null)
                    {
                        basketAllocation.CurrentQty = row.CurrentQty;
                        basketAllocation.ReservedQty = row.ReservedQty;
                        basketAllocation.AvailableQty = row.AvailableQty;
                    }
                }

                SelectedLotRow = LotRows.FirstOrDefault(x => x.AllocationQty > 0) ?? LotRows.FirstOrDefault();
                RefreshAllocationTotals();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private decimal? ResolveDefaultAllocationQty(RawMaterialAllocationLotRowModel? row)
        {
            if (row == null)
            {
                return null;
            }

            if (row.AllocationQty > 0)
            {
                return row.AllocationQty;
            }

            var defaultQty = Math.Min(Math.Max(0m, RemainingQty), row.AvailableQty);
            return defaultQty > 0 ? defaultQty : null;
        }

        private void AssignSelectedLot()
        {
            if (SelectedLotRow == null)
            {
                _messageService.ShowWarning("배정할 원자재 LOT를 선택하세요.");
                return;
            }

            var qty = AllocationInputQty ?? 0m;

            if (qty <= 0)
            {
                _messageService.ShowWarning("배정수량은 0보다 커야 합니다.");
                return;
            }

            var maxQty = SelectedLotMaxAllocationQty;

            if (qty > maxQty)
            {
                _messageService.ShowWarning($"배정 가능한 수량을 초과했습니다.\n최대 배정 가능: {maxQty:N2}");
                return;
            }

            SelectedLotRow.AllocationQty = qty;
            if (_allocationByLotId.TryGetValue(
                    SelectedLotRow.RawMaterialInventoryLotId,
                    out var allocation))
            {
                allocation.CurrentQty = SelectedLotRow.CurrentQty;
                allocation.ReservedQty = SelectedLotRow.ReservedQty;
                allocation.AvailableQty = SelectedLotRow.AvailableQty;
                allocation.Qty = qty;
            }
            else
            {
                allocation = SelectedLotRow.ToEditModel();
                _allocationByLotId.Add(allocation.RawMaterialInventoryLotId, allocation);
                AllocationBasket.Add(allocation);
            }
            SelectedBasketAllocation = allocation;
            AllocationInputQty = ResolveDefaultAllocationQty(SelectedLotRow);
            RefreshAllocationTotals();
        }

        private void ClearSelectedLot()
        {
            if (SelectedLotRow == null)
            {
                _messageService.ShowWarning("배정을 취소할 원자재 LOT를 선택하세요.");
                return;
            }

            SelectedLotRow.AllocationQty = 0m;
            RemoveAllocationFromBasket(SelectedLotRow.RawMaterialInventoryLotId);
            AllocationInputQty = ResolveDefaultAllocationQty(SelectedLotRow);
            RefreshAllocationTotals();
        }

        private void RemoveBasketAllocation()
        {
            if (SelectedBasketAllocation == null)
            {
                _messageService.ShowWarning("삭제할 현재 배정 내역을 선택하세요.");
                return;
            }

            var lotId = SelectedBasketAllocation.RawMaterialInventoryLotId;
            RemoveAllocationFromBasket(lotId);
            var visibleRow = LotRows.FirstOrDefault(x => x.RawMaterialInventoryLotId == lotId);
            if (visibleRow != null)
            {
                visibleRow.AllocationQty = 0m;
                if (ReferenceEquals(SelectedLotRow, visibleRow))
                {
                    AllocationInputQty = ResolveDefaultAllocationQty(visibleRow);
                }
            }
            RefreshAllocationTotals();
        }

        private void RemoveAllocationFromBasket(long rawMaterialInventoryLotId)
        {
            if (!_allocationByLotId.Remove(rawMaterialInventoryLotId, out var allocation))
            {
                return;
            }

            AllocationBasket.Remove(allocation);
            if (ReferenceEquals(SelectedBasketAllocation, allocation))
            {
                SelectedBasketAllocation = null;
            }
        }

        private void RefreshAllocationTotals()
        {
            OnPropertyChanged(nameof(TotalAllocationQty));
            OnPropertyChanged(nameof(RemainingQty));
            OnPropertyChanged(nameof(SelectedLotMaxAllocationQty));
        }

        private void Apply()
        {
            foreach (var allocation in AllocationBasket)
            {
                if (allocation.Qty <= 0)
                {
                    _messageService.ShowWarning("배정수량은 0보다 커야 합니다.");
                    return;
                }

                if (_loadedLotIds.Contains(allocation.RawMaterialInventoryLotId)
                    && allocation.Qty > allocation.AvailableQty)
                {
                    _messageService.ShowWarning($"가용수량보다 크게 배정할 수 없습니다.\nLOT: {allocation.LotNo}");
                    return;
                }
            }

            if (RequiredQty > 0 && TotalAllocationQty != RequiredQty)
            {
                _messageService.ShowWarning($"배정수량 합계가 사용 M수와 일치해야 합니다.\n사용 M수: {RequiredQty:N2} / 배정: {TotalAllocationQty:N2}");
                return;
            }

            AppliedAllocations.Clear();

            foreach (var allocation in AllocationBasket)
            {
                AppliedAllocations.Add(CloneAllocation(allocation, allocation.Qty));
            }

            OwnerWindow!.DialogResult = true;
            OwnerWindow.Close();
        }

        private void Cancel()
        {
            OwnerWindow!.DialogResult = false;
            OwnerWindow.Close();
        }

        private static OutsourceWorkInstructionRawMaterialAllocationEditModel CloneAllocation(
            OutsourceWorkInstructionRawMaterialAllocationEditModel source,
            decimal qty)
        {
            return new OutsourceWorkInstructionRawMaterialAllocationEditModel
            {
                RawMaterialInventoryLotId = source.RawMaterialInventoryLotId,
                RawMaterialId = source.RawMaterialId,
                RawMaterialLocationId = source.RawMaterialLocationId,
                MaterialCode = source.MaterialCode,
                MaterialName = source.MaterialName,
                LocationName = source.LocationName,
                LotNo = source.LotNo,
                CurrentQty = source.CurrentQty,
                ReservedQty = source.ReservedQty,
                AvailableQty = source.AvailableQty,
                Qty = qty
            };
        }
    }

    public sealed class RawMaterialAllocationLotRowModel : ViewModelBase
    {
        private decimal _allocationQty;

        public long RawMaterialInventoryLotId { get; set; }
        public long RawMaterialId { get; set; }
        public long RawMaterialLocationId { get; set; }
        public string MaterialCode { get; set; } = string.Empty;
        public string MaterialName { get; set; } = string.Empty;
        public string LocationName { get; set; } = string.Empty;
        public string LotNo { get; set; } = string.Empty;
        public decimal CurrentQty { get; set; }
        public decimal ReservedQty { get; set; }
        public decimal AvailableQty { get; set; }

        public decimal AllocationQty
        {
            get => _allocationQty;
            set
            {
                if (SetProperty(ref _allocationQty, value))
                {
                    OnPropertyChanged(nameof(BalanceAfter));
                }
            }
        }

        public decimal BalanceAfter => AvailableQty - AllocationQty;

        public static RawMaterialAllocationLotRowModel FromDto(
            RawMaterialInventoryLotDto dto,
            decimal reservedQty,
            decimal allocationQty,
            decimal restorableConsumedQty)
        {
            var availableQty = Math.Max(
                0m,
                dto.CurrentQty
                + restorableConsumedQty
                - reservedQty);
            return new RawMaterialAllocationLotRowModel
            {
                RawMaterialInventoryLotId = dto.RawMaterialInventoryLotId,
                RawMaterialId = dto.RawMaterialId,
                RawMaterialLocationId = dto.RawMaterialLocationId,
                MaterialCode = dto.MaterialCode,
                MaterialName = dto.MaterialName,
                LocationName = dto.LocationName,
                LotNo = dto.LotNo,
                CurrentQty = dto.CurrentQty,
                ReservedQty = reservedQty,
                AvailableQty = availableQty,
                AllocationQty = allocationQty
            };
        }

        public OutsourceWorkInstructionRawMaterialAllocationEditModel ToEditModel()
        {
            return new OutsourceWorkInstructionRawMaterialAllocationEditModel
            {
                RawMaterialInventoryLotId = RawMaterialInventoryLotId,
                RawMaterialId = RawMaterialId,
                RawMaterialLocationId = RawMaterialLocationId,
                MaterialCode = MaterialCode,
                MaterialName = MaterialName,
                LocationName = LocationName,
                LotNo = LotNo,
                CurrentQty = CurrentQty,
                ReservedQty = ReservedQty,
                AvailableQty = AvailableQty,
                Qty = AllocationQty
            };
        }
    }

    public sealed class RawMaterialAllocationDialogContext
    {
        public RawMaterialAllocationDialogContext(
            OutsourceWorkInstructionDraftEditModel draft,
            OutsourceRawMaterialAllocationWindowViewModel viewModel)
        {
            Draft = draft;
            ViewModel = viewModel;
        }

        public OutsourceWorkInstructionDraftEditModel Draft { get; }
        public OutsourceRawMaterialAllocationWindowViewModel ViewModel { get; }
    }
}
