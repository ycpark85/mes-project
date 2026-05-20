using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Common.ViewModels;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Shipments.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Shipments.ViewModels
{
    public class ShipmentPageViewModel : CrudPageViewModelBase<ShipmentLineDto>
    {
        private const string ShipmentStatusWaiting = "WAITING";
        private const string ShipmentStatusDone = "DONE";

        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _selectedShipmentStatus = ShipmentStatusWaiting;
        private string _searchKeyword = string.Empty;
        private int _page = 1;
        private int _size = 50;
        private int _total;
        private bool _canGoPreviousPage;
        private bool _canGoNextPage;

        public ShipmentPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<ShipmentDisplayItemDto>();

            ShowWaitingCommand = new AsyncRelayCommand(async () =>
            {
                await ChangeShipmentStatusAsync(ShipmentStatusWaiting);
            });

            ShowDoneCommand = new AsyncRelayCommand(async () =>
            {
                await ChangeShipmentStatusAsync(ShipmentStatusDone);
            });

            ConfirmSelectedCommand = new AsyncRelayCommand(ConfirmSelectedAsync);
            SelectAllCommand = new RelayCommand(_ => SelectAll());
            ClearSelectionCommand = new RelayCommand(_ => ClearSelection());
            PreviousPageCommand = new AsyncRelayCommand(GoPreviousPageAsync);
            NextPageCommand = new AsyncRelayCommand(GoNextPageAsync);
        }

        public ObservableCollection<ShipmentDisplayItemDto> Items { get; }

        public AsyncRelayCommand ShowWaitingCommand { get; }
        public AsyncRelayCommand ShowDoneCommand { get; }
        public AsyncRelayCommand ConfirmSelectedCommand { get; }
        public RelayCommand SelectAllCommand { get; }
        public RelayCommand ClearSelectionCommand { get; }
        public AsyncRelayCommand PreviousPageCommand { get; }
        public AsyncRelayCommand NextPageCommand { get; }

        public string SelectedShipmentStatus
        {
            get => _selectedShipmentStatus;
            set
            {
                if (SetProperty(ref _selectedShipmentStatus, value))
                {
                    OnPropertyChanged(nameof(IsWaitingTab));
                    OnPropertyChanged(nameof(IsDoneTab));
                    OnPropertyChanged(nameof(IsConfirmEnabled));
                    OnPropertyChanged(nameof(CurrentTabTitle));
                }
            }
        }

        public bool IsWaitingTab => SelectedShipmentStatus == ShipmentStatusWaiting;
        public bool IsDoneTab => SelectedShipmentStatus == ShipmentStatusDone;
        public bool IsConfirmEnabled => IsWaitingTab && Items.Any(x => x.IsSelected);

        public string CurrentTabTitle => IsDoneTab ? "출하관리 - 출하완료" : "출하관리 - 출하대기";

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public int Page
        {
            get => _page;
            set
            {
                if (SetProperty(ref _page, value))
                {
                    OnPropertyChanged(nameof(PageInfoText));
                }
            }
        }

        public int Size
        {
            get => _size;
            set
            {
                if (SetProperty(ref _size, value))
                {
                    OnPropertyChanged(nameof(PageInfoText));
                }
            }
        }

        public int Total
        {
            get => _total;
            set
            {
                if (SetProperty(ref _total, value))
                {
                    OnPropertyChanged(nameof(PageInfoText));
                    OnPropertyChanged(nameof(TotalCountText));
                }
            }
        }

        public bool CanGoPreviousPage
        {
            get => _canGoPreviousPage;
            set => SetProperty(ref _canGoPreviousPage, value);
        }

        public bool CanGoNextPage
        {
            get => _canGoNextPage;
            set => SetProperty(ref _canGoNextPage, value);
        }

        public int SelectedCount => Items.Count(x => x.IsSelected);
        public string SelectedCountText => $"선택 {SelectedCount:N0}건";
        public string PageInfoText => $"{Page} / {Math.Max(1, (int)Math.Ceiling((double)Math.Max(Total, 1) / Math.Max(Size, 1)))} 페이지";
        public string TotalCountText => $"총 {Total:N0}건";

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        protected override async Task LoadListAsync()
        {
            var route = BuildListUrl();
            var result = await _apiClient.GetAsync<ShipmentLineListResponse>(route);

            if (!result.Success || result.Data == null)
            {
                Items.Clear();
                Total = 0;
                CanGoPreviousPage = false;
                CanGoNextPage = false;
                _messageService.ShowError(result.Message ?? "출하 목록 조회 중 오류가 발생했습니다.");
                return;
            }

            Items.Clear();

            var groupedItems = result.Data.Items
                .GroupBy(x => x.OrderLineId)
                .Select(group =>
                {
                    var first = group.First();

                    var stockLines = group
                        .Where(x => x.SourceType == "STOCK")
                        .ToList();

                    var productionLines = group
                        .Where(x => x.SourceType == "INSPECTION_RESULT")
                        .ToList();

                    var display = new ShipmentDisplayItemDto
                    {
                        OrderLineId = first.OrderLineId,
                        OrderNo = first.OrderNo,
                        PartnerName = first.PartnerName,
                        ProductCode = first.ProductCode,
                        ProductName = first.ProductName,
                        Status = first.Status,
                        ShippedDate = group
                            .Where(x => x.ShippedAt.HasValue)
                            .OrderByDescending(x => x.ShippedAt)
                            .Select(x => x.ShippedAt)
                            .FirstOrDefault(),

                        StockShipQty = stockLines.Sum(x => x.Status == "DONE" ? x.ShippedQty : x.ShipQty),
                        ProductionShipQty = productionLines.Sum(x => x.Status == "DONE" ? x.ShippedQty : x.ShipQty),

                        StockLotNos = string.Join(", ",
                            stockLines
                                .Select(x => x.LotNo)
                                .Where(x => !string.IsNullOrWhiteSpace(x))
                                .Distinct()),

                        ProductionLotNos = string.Join(", ",
                            productionLines
                                .Select(x => x.LotNo)
                                .Where(x => !string.IsNullOrWhiteSpace(x))
                                .Distinct()),

                        Lines = new ObservableCollection<ShipmentLineDto>(group)
                    };

                    return display;
                })
                .ToList();

            foreach (var item in groupedItems)
            {
                item.PropertyChanged += (_, e) =>
                {
                    if (e.PropertyName == nameof(ShipmentDisplayItemDto.IsSelected))
                    {
                        RaiseSelectionPropertiesChanged();
                    }
                };

                Items.Add(item);
            }

            Page = result.Data.Page;
            Size = result.Data.Size;
            Total = result.Data.Total;

            CanGoPreviousPage = Page > 1;
            CanGoNextPage = Page * Size < Total;

            RaiseSelectionPropertiesChanged();
            OnPropertyChanged(nameof(PageInfoText));
            OnPropertyChanged(nameof(TotalCountText));
        }

        protected override void Reset()
        {
            SearchKeyword = string.Empty;
            Page = 1;
            Size = 50;
            Total = 0;
            SelectedItem = null;
            ClearSelection();
        }

        protected override void New()
        {
        }

        protected override void OnSelectedItemChanged(ShipmentLineDto? item)
        {
        }

        private async Task ChangeShipmentStatusAsync(string targetStatus)
        {
            if (SelectedShipmentStatus == targetStatus)
            {
                return;
            }

            SelectedShipmentStatus = targetStatus;
            SearchKeyword = string.Empty;
            Page = 1;
            SelectedItem = null;
            ClearSelection();

            await SearchAsync();
        }

        private async Task ConfirmSelectedAsync()
        {
            if (!IsWaitingTab)
            {
                _messageService.ShowWarning("출하확정은 출하대기 탭에서만 가능합니다.");
                return;
            }

            var selectedIds = Items
                .Where(x => x.IsSelected)
                .SelectMany(x => x.Lines)
                .Select(x => x.ShipmentLineId)
                .Distinct()
                .ToList();

            if (selectedIds.Count == 0)
            {
                _messageService.ShowWarning("출하확정할 항목을 선택하세요.");
                return;
            }

            var confirmed = _messageService.Confirm(
                $"선택한 {selectedIds.Count:N0}건을 출하확정 처리하시겠습니까?\n출하확정 시 실제 재고가 차감됩니다.",
                "출하확정 확인");

            if (!confirmed)
            {
                return;
            }

            IsLoading = true;

            try
            {
                var request = new ShipmentConfirmRequest
                {
                    ShipmentLineIds = new ObservableCollection<int>(selectedIds)
                };

                var route = $"{ApiRoutes.Shipments}/confirm";
                var result = await _apiClient.PostAsync<ShipmentConfirmRequest, ShipmentConfirmResponse>(route, request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "출하확정 처리 중 오류가 발생했습니다.");
                    return;
                }

                await SearchAsync();

                _messageService.ShowInfo($"{result.Data.ConfirmedCount:N0}건 출하확정 처리되었습니다.");
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void SelectAll()
        {
            if (!IsWaitingTab)
            {
                return;
            }

            foreach (var item in Items)
            {
                item.IsSelected = true;
            }

            RaiseSelectionPropertiesChanged();
        }

        private void ClearSelection()
        {
            foreach (var item in Items)
            {
                item.IsSelected = false;
            }

            RaiseSelectionPropertiesChanged();
        }

        private void RaiseSelectionPropertiesChanged()
        {
            OnPropertyChanged(nameof(SelectedCount));
            OnPropertyChanged(nameof(SelectedCountText));
            OnPropertyChanged(nameof(IsConfirmEnabled));
        }

        private string BuildListUrl()
        {
            var page = Page <= 0 ? 1 : Page;
            var size = Size <= 0 ? 50 : Size;

            var queryParts = new List<string>
            {
                $"status={Uri.EscapeDataString(SelectedShipmentStatus)}",
                $"page={page}",
                $"size={size}"
            };

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }

            return $"{ApiRoutes.Shipments}?{string.Join("&", queryParts)}";
        }

        private async Task GoPreviousPageAsync()
        {
            if (!CanGoPreviousPage)
            {
                return;
            }

            Page--;
            await SearchAsync();
        }

        private async Task GoNextPageAsync()
        {
            if (!CanGoNextPage)
            {
                return;
            }

            Page++;
            await SearchAsync();
        }
    }
}