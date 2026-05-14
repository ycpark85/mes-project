using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Common.ViewModels;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Inventories.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Inventories.ViewModels
{
    public class InventoryPageViewModel : CrudPageViewModelBase<InventoryDto>
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _searchKeyword = string.Empty;
        private string _selectedMovementType = "전체";
        private int _adjustmentQty;
        private string _adjustmentMemo = string.Empty;

        public InventoryPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<InventoryDto>();
            Movements = new ObservableCollection<InventoryMovementDto>();
            MovementTypeOptions = new ObservableCollection<string>
            {
                "전체",
                "기초재고",
                "검수입고",
                "출고",
                "재고증가",
                "재고감소"
            };

            EditModel = new InventoryEditModel();

            AdjustInCommand = new AsyncRelayCommand(AdjustInAsync);
            AdjustOutCommand = new AsyncRelayCommand(AdjustOutAsync);
            OpenInitialInventoryBulkUploadCommand = new RelayCommand(OpenInitialInventoryBulkUpload);
        }

        public event Action<InitialInventoryBulkUploadWindowViewModel>? RequestOpenInitialInventoryBulkUpload;
        public RelayCommand OpenInitialInventoryBulkUploadCommand { get; }
        public ObservableCollection<InventoryDto> Items { get; }
        public ObservableCollection<InventoryMovementDto> Movements { get; }
        public ObservableCollection<string> MovementTypeOptions { get; }
        public InventoryEditModel EditModel { get; }

        public AsyncRelayCommand AdjustInCommand { get; }
        public AsyncRelayCommand AdjustOutCommand { get; }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public string SelectedMovementType
        {
            get => _selectedMovementType;
            set
            {
                if (SetProperty(ref _selectedMovementType, value))
                {
                    _ = LoadMovementsAsync();
                }
            }
        }

        public int AdjustmentQty
        {
            get => _adjustmentQty;
            set => SetProperty(ref _adjustmentQty, value);
        }

        public string AdjustmentMemo
        {
            get => _adjustmentMemo;
            set => SetProperty(ref _adjustmentMemo, value);
        }

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        protected override async Task LoadListAsync()
        {
            var result = await _apiClient.GetAsync<InventoryListDto>(BuildListUrl());

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "재고 조회 중 오류가 발생했습니다.");
                return;
            }

            Items.Clear();

            foreach (var item in result.Data.Items)
            {
                Items.Add(item);
            }
        }

        protected override void Reset()
        {
            SearchKeyword = string.Empty;
            SelectedMovementType = "전체";
            SelectedItem = null;
            EditModel.Clear();
            Movements.Clear();
            AdjustmentQty = 0;
            AdjustmentMemo = string.Empty;
        }

        protected override void New()
        {
            SelectedItem = null;
            EditModel.Clear();
            Movements.Clear();
            AdjustmentQty = 0;
            AdjustmentMemo = string.Empty;
        }

        protected override void OnSelectedItemChanged(InventoryDto? item)
        {
            if (item == null)
            {
                EditModel.Clear();
                Movements.Clear();
                return;
            }

            EditModel.LoadFromDto(item);
            _ = LoadMovementsAsync();
        }

        private async Task LoadMovementsAsync()
        {
            if (SelectedItem == null)
            {
                Movements.Clear();
                return;
            }

            var queryParts = new List<string>
            {
                $"product_id={SelectedItem.ProductId}",
                "page=1",
                "size=200"
            };

            var movementTypeCode = ToMovementTypeCode(SelectedMovementType);

            if (!string.IsNullOrWhiteSpace(movementTypeCode))
            {
                queryParts.Add($"movement_type={Uri.EscapeDataString(movementTypeCode)}");
            }

            var route = $"{ApiRoutes.InventoryMovements}?{string.Join("&", queryParts)}";

            var result = await _apiClient.GetAsync<InventoryMovementListDto>(route);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "재고 이력 조회 중 오류가 발생했습니다.");
                return;
            }

            Movements.Clear();

            foreach (var item in result.Data.Items)
            {
                Movements.Add(item);
            }
        }

        private async Task AdjustInAsync()
        {
            await AdjustAsync("IN");
        }

        private async Task AdjustOutAsync()
        {
            await AdjustAsync("OUT");
        }

        private async Task AdjustAsync(string direction)
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("재고 조정할 품목을 먼저 선택하세요.");
                return;
            }

            if (AdjustmentQty <= 0)
            {
                _messageService.ShowWarning("조정 수량은 1 이상이어야 합니다.");
                return;
            }

            var label = direction == "IN" ? "증가" : "감소";

            var confirmed = _messageService.Confirm(
                $"[{SelectedItem.ProductCode}] {SelectedItem.ProductName} 재고를 {AdjustmentQty} {SelectedItem.Uom} {label} 처리하시겠습니까?",
                "재고 조정 확인");

            if (!confirmed)
            {
                return;
            }

            IsLoading = true;

            try
            {
                var request = new InventoryAdjustmentRequest
                {
                    Qty = AdjustmentQty,
                    Memo = string.IsNullOrWhiteSpace(AdjustmentMemo) ? null : AdjustmentMemo.Trim()
                };

                var route = $"{ApiRoutes.Inventories}/{SelectedItem.ProductId}/adjust?direction={direction}";

                var result = await _apiClient.PostAsync<InventoryAdjustmentRequest, InventoryMovementDto>(
                    route,
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "재고 조정 중 오류가 발생했습니다.");
                    return;
                }

                var selectedProductId = SelectedItem.ProductId;

                await SearchAsync();

                InventoryDto? reselectedItem = null;

                foreach (var item in Items)
                {
                    if (item.ProductId == selectedProductId)
                    {
                        reselectedItem = item;
                        break;
                    }
                }

                SelectedItem = reselectedItem;

                AdjustmentQty = 0;
                AdjustmentMemo = string.Empty;

                _messageService.ShowInfo("재고 조정이 완료되었습니다.");
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
                "size=100"
            };

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }

            return $"{ApiRoutes.Inventories}?{string.Join("&", queryParts)}";
        }

        private static string ToMovementTypeCode(string movementTypeText)
        {
            return movementTypeText switch
            {
                "기초재고" => "INITIAL_STOCK",
                "검수입고" => "INSPECTION_IN",
                "출고" => "SHIP_OUT",
                "재고증가" => "ADJUST_IN",
                "재고감소" => "ADJUST_OUT",
                _ => string.Empty
            };
        }

        private void OpenInitialInventoryBulkUpload()
        {
            var viewModel = new InitialInventoryBulkUploadWindowViewModel(_apiClient, _messageService);

            viewModel.UploadCompleted += () =>
            {
                _ = SearchAsync();
            };

            RequestOpenInitialInventoryBulkUpload?.Invoke(viewModel);
        }

    }
}