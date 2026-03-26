using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Common.ViewModels;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OrderLineList.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.OrderLineList.ViewModels
{
    public class OrderLineListPageViewModel : CrudPageViewModelBase<OrderLineListItemDto>
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly Func<long, Task>? _openDetailAsync;
        private readonly Func<OrderLineListItemDto, Task>? _openLotCreateAsync;

        private string _searchKeyword = string.Empty;
        private string _selectedStatus = "전체";
        private int _page = 1;
        private int _size = 20;
        private int _total;
        private DateTime? _orderDateFrom;
        private DateTime? _orderDateTo;
        private bool _canGoPreviousPage;
        private bool _canGoNextPage;

        public OrderLineListPageViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            Func<long, Task>? openDetailAsync = null,
            Func<OrderLineListItemDto, Task>? openLotCreateAsync = null)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _openDetailAsync = openDetailAsync;
            _openLotCreateAsync = openLotCreateAsync;

            Items = new ObservableCollection<OrderLineListItemDto>();
            StatusOptions = new ObservableCollection<string> { "전체", "OPEN", "IN_PROGRESS", "DONE", "CANCELED" };

            SearchCommand = new AsyncRelayCommand(async () =>
            {
                Page = 1;
                await SearchAsync();
            });
            ResetCommand = new RelayCommand(Reset);
            OpenOrderDetailCommand = new AsyncRelayCommand(OpenOrderDetailAsync);
            OpenLotActionCommand = new AsyncRelayCommand(OpenLotActionAsync);
            PreviousPageCommand = new AsyncRelayCommand(GoPreviousPageAsync);
            NextPageCommand = new AsyncRelayCommand(GoNextPageAsync);
        }

        public ObservableCollection<OrderLineListItemDto> Items { get; }
        public ObservableCollection<string> StatusOptions { get; }

        public AsyncRelayCommand SearchCommand { get; }
        public RelayCommand ResetCommand { get; }
        public AsyncRelayCommand OpenOrderDetailCommand { get; }
        public AsyncRelayCommand OpenLotActionCommand { get; }
        public AsyncRelayCommand PreviousPageCommand { get; }
        public AsyncRelayCommand NextPageCommand { get; }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public string SelectedStatus
        {
            get => _selectedStatus;
            set => SetProperty(ref _selectedStatus, value);
        }

        public DateTime? OrderDateFrom
        {
            get => _orderDateFrom;
            set => SetProperty(ref _orderDateFrom, value);
        }

        public DateTime? OrderDateTo
        {
            get => _orderDateTo;
            set => SetProperty(ref _orderDateTo, value);
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

        public string PageInfoText => $"{Page} / {Math.Max(1, (int)Math.Ceiling((double)Math.Max(Total, 1) / Size))} 페이지 (총 {Total}건)";

        public string LotActionButtonText
        {
            get
            {
                if (SelectedItem == null)
                {
                    return "LOT 생성";
                }

                return SelectedItem.HasLot ? "LOT 상세" : "LOT 생성";
            }
        }

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        protected override async Task LoadListAsync()
        {
            var route = BuildListUrl();
            var result = await _apiClient.GetAsync<OrderLineListResponse>(route);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "수주 리스트 조회 중 오류가 발생했습니다.");
                return;
            }

            Items.Clear();

            foreach (var item in result.Data.Items)
                Items.Add(item);

            Page = result.Data.Meta.Page;
            Size = result.Data.Meta.Size;
            Total = result.Data.Meta.Total;

            CanGoPreviousPage = Page > 1;
            CanGoNextPage = Page * Size < Total;

            OnPropertyChanged(nameof(PageInfoText));
        }

        protected override void Reset()
        {
            SearchKeyword = string.Empty;
            SelectedStatus = "전체";
            OrderDateFrom = null;
            OrderDateTo = null;
            Page = 1;
            Size = 20;
            Total = 0;
            CanGoPreviousPage = false;
            CanGoNextPage = false;
            SelectedItem = null;

            OnPropertyChanged(nameof(PageInfoText));
        }

        protected override void New()
        {
        }

        protected override void OnSelectedItemChanged(OrderLineListItemDto? item)
        {
            OnPropertyChanged(nameof(LotActionButtonText));
        }

        private async Task OpenOrderDetailAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("발주상세를 볼 항목을 먼저 선택하세요.");
                return;
            }

            if (_openDetailAsync == null)
            {
                _messageService.ShowWarning("상세 화면 연결이 아직 설정되지 않았습니다.");
                return;
            }

            await _openDetailAsync(SelectedItem.OrderLineId);
        }

        private async Task OpenLotActionAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("항목을 먼저 선택하세요.");
                return;
            }

            if (!string.Equals(SelectedItem.Status, "OPEN", StringComparison.OrdinalIgnoreCase))
            {
                _messageService.ShowWarning("LOT 생성은 OPEN 상태의 수주라인에서만 가능합니다.");
                return;
            }

            if (_openLotCreateAsync == null)
            {
                _messageService.ShowWarning("LOT 생성 창 연결이 아직 설정되지 않았습니다.");
                return;
            }

            await _openLotCreateAsync(SelectedItem);
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string>
            {
                $"page={Page}",
                $"size={Size}"
            };

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");

            if (!string.IsNullOrWhiteSpace(SelectedStatus) && SelectedStatus != "전체")
            {
                var apiStatus = SelectedStatus == "IN_PROGRESS" ? "CLOSED" : SelectedStatus;
                queryParts.Add($"status={Uri.EscapeDataString(apiStatus)}");
            }

            if (OrderDateFrom.HasValue)
                queryParts.Add($"order_date_from={OrderDateFrom.Value:yyyy-MM-dd}");

            if (OrderDateTo.HasValue)
                queryParts.Add($"order_date_to={OrderDateTo.Value:yyyy-MM-dd}");

            return $"{ApiRoutes.OrderLines}?{string.Join("&", queryParts)}";
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