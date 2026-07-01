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
    public class RawMaterialMovementTypeOption
    {
        public RawMaterialMovementTypeOption(string code, string displayName)
        {
            Code = code;
            DisplayName = displayName;
        }

        public string Code { get; }
        public string DisplayName { get; }
    }

    public class RawMaterialInventoryPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private RawMaterialInventoryLotDto? _selectedInventoryLot;
        private RawMaterialDto? _selectedInboundMaterial;
        private RawMaterialLocationDto? _selectedInboundLocation;
        private RawMaterialLocationDto? _selectedTransferToLocation;
        private RawMaterialDto? _selectedMovementMaterial;
        private RawMaterialLocationDto? _selectedMovementLocation;
        private string _searchKeyword = string.Empty;
        private string _inboundLotNo = string.Empty;
        private string _movementLotNo = string.Empty;
        private string _selectedMovementType = string.Empty;
        private DateTime? _movementDateFrom;
        private DateTime? _movementDateTo;
        private decimal _inboundQty;
        private decimal? _inboundUnitCost;
        private decimal _workQty;
        private string _memo = string.Empty;

        public RawMaterialInventoryPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            InventoryLots = new ObservableCollection<RawMaterialInventoryLotDto>();
            Materials = new ObservableCollection<RawMaterialDto>();
            Locations = new ObservableCollection<RawMaterialLocationDto>();
            Movements = new ObservableCollection<RawMaterialMovementDto>();
            MovementTypeOptions = new ObservableCollection<RawMaterialMovementTypeOption>
            {
                new(string.Empty, "\uC804\uCCB4"),
                new("INBOUND", "\uC785\uACE0"),
                new("TRANSFER_OUT", "\uC774\uB3D9\uCD9C\uACE0"),
                new("TRANSFER_IN", "\uC774\uB3D9\uC785\uACE0"),
                new("ADJUST_IN", "\uC7AC\uACE0\uC99D\uAC00"),
                new("ADJUST_OUT", "\uC7AC\uACE0\uAC10\uC18C"),
                new("CONSUME_OUT", "\uC0AC\uC6A9\uCC28\uAC10"),
                new("CONSUME_REVERSE", "\uC0AC\uC6A9\uCDE8\uC18C")
            };
            RefreshCommand = new AsyncRelayCommand(InitializeAsync);
            RefreshMovementsCommand = new AsyncRelayCommand(LoadMovementsAsync);
            InboundCommand = new AsyncRelayCommand(InboundAsync);
            TransferCommand = new AsyncRelayCommand(TransferAsync);
            AdjustInCommand = new AsyncRelayCommand(() => AdjustAsync("IN"));
            AdjustOutCommand = new AsyncRelayCommand(() => AdjustAsync("OUT"));
        }

        public ObservableCollection<RawMaterialInventoryLotDto> InventoryLots { get; }
        public ObservableCollection<RawMaterialDto> Materials { get; }
        public ObservableCollection<RawMaterialLocationDto> Locations { get; }
        public ObservableCollection<RawMaterialMovementDto> Movements { get; }
        public ObservableCollection<RawMaterialMovementTypeOption> MovementTypeOptions { get; }
        public AsyncRelayCommand RefreshCommand { get; }
        public AsyncRelayCommand RefreshMovementsCommand { get; }
        public AsyncRelayCommand InboundCommand { get; }
        public AsyncRelayCommand TransferCommand { get; }
        public AsyncRelayCommand AdjustInCommand { get; }
        public AsyncRelayCommand AdjustOutCommand { get; }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public RawMaterialInventoryLotDto? SelectedInventoryLot
        {
            get => _selectedInventoryLot;
            set
            {
                if (SetProperty(ref _selectedInventoryLot, value))
                {
                    ApplyMovementFilterFromLot(value);
                    _ = LoadMovementsAsync();
                }
            }
        }

        public RawMaterialDto? SelectedInboundMaterial
        {
            get => _selectedInboundMaterial;
            set => SetProperty(ref _selectedInboundMaterial, value);
        }

        public RawMaterialLocationDto? SelectedInboundLocation
        {
            get => _selectedInboundLocation;
            set => SetProperty(ref _selectedInboundLocation, value);
        }

        public RawMaterialLocationDto? SelectedTransferToLocation
        {
            get => _selectedTransferToLocation;
            set => SetProperty(ref _selectedTransferToLocation, value);
        }

        public RawMaterialDto? SelectedMovementMaterial
        {
            get => _selectedMovementMaterial;
            set => SetProperty(ref _selectedMovementMaterial, value);
        }

        public RawMaterialLocationDto? SelectedMovementLocation
        {
            get => _selectedMovementLocation;
            set => SetProperty(ref _selectedMovementLocation, value);
        }

        public string InboundLotNo
        {
            get => _inboundLotNo;
            set => SetProperty(ref _inboundLotNo, value);
        }

        public string MovementLotNo
        {
            get => _movementLotNo;
            set => SetProperty(ref _movementLotNo, value);
        }

        public string SelectedMovementType
        {
            get => _selectedMovementType;
            set => SetProperty(ref _selectedMovementType, value);
        }

        public DateTime? MovementDateFrom
        {
            get => _movementDateFrom;
            set => SetProperty(ref _movementDateFrom, value);
        }

        public DateTime? MovementDateTo
        {
            get => _movementDateTo;
            set => SetProperty(ref _movementDateTo, value);
        }

        public decimal InboundQty
        {
            get => _inboundQty;
            set => SetProperty(ref _inboundQty, value);
        }

        public decimal? InboundUnitCost
        {
            get => _inboundUnitCost;
            set => SetProperty(ref _inboundUnitCost, value);
        }

        public decimal WorkQty
        {
            get => _workQty;
            set => SetProperty(ref _workQty, value);
        }

        public string Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public async Task InitializeAsync()
        {
            await LoadMastersAsync();
            await LoadInventoryLotsAsync();
        }

        private async Task LoadMastersAsync()
        {
            var materialResult = await _apiClient.GetAsync<RawMaterialListDto>($"{ApiRoutes.RawMaterials}?page=1&size=200&is_active=true");
            if (materialResult.Success && materialResult.Data != null)
            {
                Materials.Clear();
                foreach (var item in materialResult.Data.Items)
                {
                    Materials.Add(item);
                }
            }

            var locationResult = await _apiClient.GetAsync<RawMaterialLocationListDto>($"{ApiRoutes.RawMaterialLocations}?page=1&size=200&is_active=true");
            if (locationResult.Success && locationResult.Data != null)
            {
                Locations.Clear();
                foreach (var item in locationResult.Data.Items)
                {
                    Locations.Add(item);
                }
            }
        }

        private async Task LoadInventoryLotsAsync()
        {
            var queryParts = new List<string> { "page=1", "size=200" };
            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }
            var result = await _apiClient.GetAsync<RawMaterialInventoryLotListDto>($"{ApiRoutes.RawMaterialInventoryLots}?{string.Join("&", queryParts)}");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "\uC6D0\uC790\uC7AC \uC7AC\uACE0 \uC870\uD68C \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
                return;
            }
            InventoryLots.Clear();
            foreach (var item in result.Data.Items)
            {
                InventoryLots.Add(item);
            }
        }

        private async Task LoadMovementsAsync()
        {
            var queryParts = new List<string> { "page=1", "size=200" };
            if (SelectedMovementMaterial != null)
            {
                queryParts.Add($"raw_material_id={SelectedMovementMaterial.RawMaterialId}");
            }
            if (SelectedMovementLocation != null)
            {
                queryParts.Add($"location_id={SelectedMovementLocation.RawMaterialLocationId}");
            }
            if (!string.IsNullOrWhiteSpace(MovementLotNo))
            {
                queryParts.Add($"lot_no={Uri.EscapeDataString(MovementLotNo.Trim())}");
            }
            if (!string.IsNullOrWhiteSpace(SelectedMovementType))
            {
                queryParts.Add($"movement_type={Uri.EscapeDataString(SelectedMovementType.Trim())}");
            }
            if (MovementDateFrom.HasValue)
            {
                queryParts.Add($"date_from={MovementDateFrom.Value:yyyy-MM-dd}");
            }
            if (MovementDateTo.HasValue)
            {
                queryParts.Add($"date_to={MovementDateTo.Value:yyyy-MM-dd}");
            }

            var result = await _apiClient.GetAsync<RawMaterialMovementListDto>($"{ApiRoutes.RawMaterialMovements}?{string.Join("&", queryParts)}");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "\uC6D0\uC790\uC7AC \uC218\uBD88 \uC870\uD68C \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
                return;
            }
            Movements.Clear();
            foreach (var item in result.Data.Items)
            {
                Movements.Add(item);
            }
        }

        private async Task InboundAsync()
        {
            if (SelectedInboundMaterial == null || SelectedInboundLocation == null)
            {
                _messageService.ShowWarning("\uC785\uACE0\uD560 \uC6D0\uC790\uC7AC \uD488\uBAA9\uACFC \uC704\uCE58\uB97C \uC120\uD0DD\uD558\uC138\uC694.");
                return;
            }
            if (string.IsNullOrWhiteSpace(InboundLotNo) || InboundQty <= 0)
            {
                _messageService.ShowWarning("\uC785\uACE0 LOT\uC640 \uC785\uACE0\uC218\uB7C9\uC744 \uC785\uB825\uD558\uC138\uC694.");
                return;
            }

            var inboundMaterial = SelectedInboundMaterial;
            var inboundLotNo = InboundLotNo.Trim();
            var request = new RawMaterialInboundRequest
            {
                RawMaterialId = inboundMaterial.RawMaterialId,
                RawMaterialLocationId = SelectedInboundLocation.RawMaterialLocationId,
                LotNo = inboundLotNo,
                Qty = InboundQty,
                UnitCost = InboundUnitCost,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim()
            };
            var result = await _apiClient.PostAsync<RawMaterialInboundRequest, RawMaterialMovementDto>(ApiRoutes.RawMaterialInbound, request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "\uC6D0\uC790\uC7AC \uC785\uACE0 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
                return;
            }
            ClearWorkInputs();
            await LoadInventoryLotsAsync();
            SelectedMovementMaterial = inboundMaterial;
            MovementLotNo = inboundLotNo;
            SelectedMovementLocation = null;
            await LoadMovementsAsync();
            _messageService.ShowInfo("\uC785\uACE0 \uCC98\uB9AC\uD588\uC2B5\uB2C8\uB2E4.");
        }

        private async Task TransferAsync()
        {
            if (SelectedInventoryLot == null || SelectedTransferToLocation == null || WorkQty <= 0)
            {
                _messageService.ShowWarning("\uC774\uB3D9\uD560 LOT, \uC774\uB3D9 \uC704\uCE58, \uC218\uB7C9\uC744 \uC785\uB825\uD558\uC138\uC694.");
                return;
            }

            var sourceLot = SelectedInventoryLot;
            var request = new RawMaterialTransferRequest
            {
                RawMaterialInventoryLotId = sourceLot.RawMaterialInventoryLotId,
                ToLocationId = SelectedTransferToLocation.RawMaterialLocationId,
                Qty = WorkQty,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim()
            };
            var result = await _apiClient.PostAsync<RawMaterialTransferRequest, RawMaterialMovementListDto>(ApiRoutes.RawMaterialTransfer, request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "\uC6D0\uC790\uC7AC \uC704\uCE58\uC774\uB3D9 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
                return;
            }
            ClearWorkInputs();
            await LoadInventoryLotsAsync();
            ApplyMovementFilterFromLot(sourceLot);
            await LoadMovementsAsync();
            _messageService.ShowInfo("\uC704\uCE58\uC774\uB3D9 \uCC98\uB9AC\uD588\uC2B5\uB2C8\uB2E4.");
        }

        private async Task AdjustAsync(string direction)
        {
            if (SelectedInventoryLot == null || WorkQty <= 0)
            {
                _messageService.ShowWarning("\uC870\uC815\uD560 LOT\uC640 \uC218\uB7C9\uC744 \uC785\uB825\uD558\uC138\uC694.");
                return;
            }

            var adjustedLot = SelectedInventoryLot;
            var request = new RawMaterialAdjustmentRequest
            {
                RawMaterialInventoryLotId = adjustedLot.RawMaterialInventoryLotId,
                Qty = WorkQty,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim()
            };
            var result = await _apiClient.PostAsync<RawMaterialAdjustmentRequest, RawMaterialMovementDto>($"{ApiRoutes.RawMaterialAdjust}?direction={direction}", request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "\uC6D0\uC790\uC7AC \uC870\uC815 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.");
                return;
            }
            ClearWorkInputs();
            await LoadInventoryLotsAsync();
            ApplyMovementFilterFromLot(adjustedLot);
            await LoadMovementsAsync();
            _messageService.ShowInfo("\uC870\uC815 \uCC98\uB9AC\uD588\uC2B5\uB2C8\uB2E4.");
        }

        private void ApplyMovementFilterFromLot(RawMaterialInventoryLotDto? lot)
        {
            if (lot == null)
            {
                return;
            }

            SelectedMovementMaterial = Materials.FirstOrDefault(x => x.RawMaterialId == lot.RawMaterialId);
            MovementLotNo = lot.LotNo;
            SelectedMovementLocation = null;
        }

        private void ClearWorkInputs()
        {
            InboundLotNo = string.Empty;
            InboundQty = 0;
            InboundUnitCost = null;
            WorkQty = 0;
            Memo = string.Empty;
        }
    }
}
