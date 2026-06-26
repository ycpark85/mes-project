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
    public class RawMaterialInventoryPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private RawMaterialInventoryLotDto? _selectedInventoryLot;
        private RawMaterialDto? _selectedInboundMaterial;
        private RawMaterialLocationDto? _selectedInboundLocation;
        private RawMaterialLocationDto? _selectedTransferToLocation;
        private string _searchKeyword = string.Empty;
        private string _inboundLotNo = string.Empty;
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
            RefreshCommand = new AsyncRelayCommand(InitializeAsync);
            InboundCommand = new AsyncRelayCommand(InboundAsync);
            TransferCommand = new AsyncRelayCommand(TransferAsync);
            AdjustInCommand = new AsyncRelayCommand(() => AdjustAsync("IN"));
            AdjustOutCommand = new AsyncRelayCommand(() => AdjustAsync("OUT"));
        }

        public ObservableCollection<RawMaterialInventoryLotDto> InventoryLots { get; }
        public ObservableCollection<RawMaterialDto> Materials { get; }
        public ObservableCollection<RawMaterialLocationDto> Locations { get; }
        public ObservableCollection<RawMaterialMovementDto> Movements { get; }
        public AsyncRelayCommand RefreshCommand { get; }
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

        public string InboundLotNo
        {
            get => _inboundLotNo;
            set => SetProperty(ref _inboundLotNo, value);
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
                _messageService.ShowError(result.Message ?? "원자재 재고 조회 중 오류가 발생했습니다.");
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
            if (SelectedInventoryLot == null)
            {
                Movements.Clear();
                return;
            }
            var result = await _apiClient.GetAsync<RawMaterialMovementListDto>($"{ApiRoutes.RawMaterialMovements}?inventory_lot_id={SelectedInventoryLot.RawMaterialInventoryLotId}&page=1&size=100");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "원자재 수불 조회 중 오류가 발생했습니다.");
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
                _messageService.ShowWarning("입고할 원자재 품목과 위치를 선택하세요.");
                return;
            }
            if (string.IsNullOrWhiteSpace(InboundLotNo) || InboundQty <= 0)
            {
                _messageService.ShowWarning("입고 LOT와 입고수량을 입력하세요.");
                return;
            }
            var request = new RawMaterialInboundRequest
            {
                RawMaterialId = SelectedInboundMaterial.RawMaterialId,
                RawMaterialLocationId = SelectedInboundLocation.RawMaterialLocationId,
                LotNo = InboundLotNo.Trim(),
                Qty = InboundQty,
                UnitCost = InboundUnitCost,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim()
            };
            var result = await _apiClient.PostAsync<RawMaterialInboundRequest, RawMaterialMovementDto>(ApiRoutes.RawMaterialInbound, request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "원자재 입고 중 오류가 발생했습니다.");
                return;
            }
            ClearWorkInputs();
            await LoadInventoryLotsAsync();
            _messageService.ShowInfo("입고 처리되었습니다.");
        }

        private async Task TransferAsync()
        {
            if (SelectedInventoryLot == null || SelectedTransferToLocation == null || WorkQty <= 0)
            {
                _messageService.ShowWarning("이동할 LOT, 이동 위치, 수량을 입력하세요.");
                return;
            }
            var request = new RawMaterialTransferRequest
            {
                RawMaterialInventoryLotId = SelectedInventoryLot.RawMaterialInventoryLotId,
                ToLocationId = SelectedTransferToLocation.RawMaterialLocationId,
                Qty = WorkQty,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim()
            };
            var result = await _apiClient.PostAsync<RawMaterialTransferRequest, RawMaterialMovementListDto>(ApiRoutes.RawMaterialTransfer, request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "원자재 위치이동 중 오류가 발생했습니다.");
                return;
            }
            ClearWorkInputs();
            await LoadInventoryLotsAsync();
            _messageService.ShowInfo("위치이동 처리되었습니다.");
        }

        private async Task AdjustAsync(string direction)
        {
            if (SelectedInventoryLot == null || WorkQty <= 0)
            {
                _messageService.ShowWarning("조정할 LOT와 수량을 입력하세요.");
                return;
            }
            var request = new RawMaterialAdjustmentRequest
            {
                RawMaterialInventoryLotId = SelectedInventoryLot.RawMaterialInventoryLotId,
                Qty = WorkQty,
                Memo = string.IsNullOrWhiteSpace(Memo) ? null : Memo.Trim()
            };
            var result = await _apiClient.PostAsync<RawMaterialAdjustmentRequest, RawMaterialMovementDto>($"{ApiRoutes.RawMaterialAdjust}?direction={direction}", request);
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "원자재 조정 중 오류가 발생했습니다.");
                return;
            }
            ClearWorkInputs();
            await LoadInventoryLotsAsync();
            _messageService.ShowInfo("조정 처리되었습니다.");
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
