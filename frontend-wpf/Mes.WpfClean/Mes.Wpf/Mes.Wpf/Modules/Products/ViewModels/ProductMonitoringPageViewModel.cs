using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Lots.Dtos;
using Mes.Wpf.Modules.Products.Dtos;


namespace Mes.Wpf.Modules.Products.ViewModels
{
    public class ProductMonitoringPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly IDrawingViewer _drawingViewer;

        private string _searchKeyword = string.Empty;
        private string _selectedUseYn = "사용";
        private bool _isLoading;
        private string _loadingMessage = "처리 중입니다...";
        private ProductDto? _selectedProduct;
        private LotListItemDto? _selectedLot;

        public ProductMonitoringPageViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            IDrawingViewer drawingViewer)
        {
            _apiClient = apiClient;
            _messageService = messageService;   
            _drawingViewer = drawingViewer;

            ProductItems = new ObservableCollection<ProductDto>();
            LotItems = new ObservableCollection<LotListItemDto>();
            UseYnOptions = new ObservableCollection<string> { "사용", "미사용" };

            SearchCommand = new AsyncRelayCommand(SearchAsync);
            ResetCommand = new AsyncRelayCommand(ResetAsync);
            LoadHistoryCommand = new AsyncRelayCommand(LoadHistoryAsync);
            OpenLotDetailCommand = new RelayCommand(_ => OpenLotDetail());
           
        }

        public event Action<long>? RequestOpenLotDetail;

        public ObservableCollection<ProductDto> ProductItems { get; }

        public ObservableCollection<LotListItemDto> LotItems { get; }

        public ObservableCollection<string> UseYnOptions { get; }

        public ICommand SearchCommand { get; }

        public ICommand ResetCommand { get; }

        public ICommand LoadHistoryCommand { get; }

        public ICommand OpenLotDetailCommand { get; }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public string SelectedUseYn
        {
            get => _selectedUseYn;
            set => SetProperty(ref _selectedUseYn, value);
        }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public string LoadingMessage
        {
            get => _loadingMessage;
            set => SetProperty(ref _loadingMessage, value);
        }

        public ProductDto? SelectedProduct
        {
            get => _selectedProduct;
            set
            {
                if (SetProperty(ref _selectedProduct, value))
                {
                    SelectedLot = null;
                    OnPropertyChanged(nameof(SelectedProductName));
                    OnPropertyChanged(nameof(SelectedProductSummaryText));
                }
            }
        }

        public LotListItemDto? SelectedLot
        {
            get => _selectedLot;
            set => SetProperty(ref _selectedLot, value);
        }

        public string SelectedProductName => SelectedProduct?.ProductName ?? "-";

        public string SelectedProductSummaryText
        {
            get
            {
                if (SelectedProduct == null)
                {
                    return "품목을 선택하세요.";
                }

                return $"{SelectedProduct.ProductCode} / {SelectedProduct.ProductName}";
            }
        }

        public string LotCountText => $"{LotItems.Count}건 표시";

        public IApiClient ApiClient => _apiClient;

        public IMessageService MessageService => _messageService;

        public Task InitializeAsync()
        {
            ProductItems.Clear();
            LotItems.Clear();

            SelectedProduct = null;
            SelectedLot = null;

            OnPropertyChanged(nameof(SelectedProductName));
            OnPropertyChanged(nameof(SelectedProductSummaryText));
            OnPropertyChanged(nameof(LotCountText));

            return Task.CompletedTask;
        }

        private async Task SearchAsync()
        {
            try
            {
                IsLoading = true;
                LoadingMessage = "품목을 조회 중입니다...";

                var route = BuildProductSearchUrl();

                var result = await _apiClient.GetAsync<ProductListResponse>(route);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "품목 목록을 조회하지 못했습니다.");
                    return;
                }

                ProductItems.Clear();

                foreach (var item in result.Data.Items)
                {
                    ProductItems.Add(item);
                }

                SelectedProduct = null;
                SelectedLot = null;
                LotItems.Clear();
                OnPropertyChanged(nameof(LotCountText));
            }
            finally
            {
                IsLoading = false;
            }
        }

        private Task ResetAsync()
        {
            SearchKeyword = string.Empty;
            SelectedUseYn = "사용";

            SelectedProduct = null;
            SelectedLot = null;

            ProductItems.Clear();
            LotItems.Clear();

            OnPropertyChanged(nameof(SelectedProductName));
            OnPropertyChanged(nameof(SelectedProductSummaryText));
            OnPropertyChanged(nameof(LotCountText));

            return Task.CompletedTask;
        }

        private async Task LoadHistoryAsync()
        {
            if (SelectedProduct == null)
            {
                _messageService.ShowWarning("품목을 먼저 선택하세요.");
                return;
            }

            if (SelectedProduct.ProductId <= 0)
            {
                _messageService.ShowWarning("품목 정보가 없습니다.");
                return;
            }

            try
            {
                IsLoading = true;
                LoadingMessage = "LOT 이력을 조회 중입니다...";

                var route =
                    $"{ApiRoutes.Lots}?product_id={SelectedProduct.ProductId}&page=1&size=10&sort=latest";

                var result = await _apiClient.GetAsync<LotListResponseDto>(route);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "LOT 이력을 조회하지 못했습니다.");
                    return;
                }

                LotItems.Clear();

                foreach (var item in result.Data.Items)
                {
                    LotItems.Add(item);
                }

                SelectedLot = null;
                OnPropertyChanged(nameof(LotCountText));
                OnPropertyChanged(nameof(SelectedProductName));
                OnPropertyChanged(nameof(SelectedProductSummaryText));
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void OpenLotDetail()
        {
            if (SelectedLot == null)
            {
                _messageService.ShowWarning("LOT를 먼저 선택하세요.");
                return;
            }

            if (SelectedLot.LotId <= 0)
            {
                _messageService.ShowWarning("LOT 정보가 없습니다.");
                return;
            }

            RequestOpenLotDetail?.Invoke(SelectedLot.LotId);
        }

        public async Task OpenDrawingAsync(ProductDto? product)
        {
            if (product == null)
            {
                _messageService.ShowWarning("품목을 먼저 선택하세요.");
                return;
            }

            if (product.DrawingId <= 0)
            {
                _messageService.ShowWarning("등록된 도면이 없습니다.");
                return;
            }

            try
            {
                IsLoading = true;
                LoadingMessage = "도면 파일을 여는 중입니다...";

                await Task.Yield();

                await _drawingViewer.OpenCurrentDrawingAsync(product.DrawingId);
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }


        private string BuildProductSearchUrl()
        {
            var route = $"{ApiRoutes.Products}?page=1&size=100";

            var keyword = SearchKeyword?.Trim();

            if (!string.IsNullOrWhiteSpace(keyword))
            {
                route += $"&q={Uri.EscapeDataString(keyword)}";
            }

            if (SelectedUseYn == "사용")
            {
                route += "&is_active=true";
            }
            else if (SelectedUseYn == "미사용")
            {
                route += "&is_active=false";
            }

            return route;
        }
    }
}