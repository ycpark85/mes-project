using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OrderLines.Dtos;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Products.ViewModels
{
    public class ProductLookupWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _keyword = string.Empty;
        private bool _isLoading;
        private OrderLineProductLookupDto? _selectedItem;

        public ProductLookupWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            string? initialKeyword = null)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<OrderLineProductLookupDto>();
            SearchCommand = new AsyncRelayCommand(SearchAsync);

            Keyword = initialKeyword?.Trim() ?? string.Empty;
        }

        public ObservableCollection<OrderLineProductLookupDto> Items { get; }

        public AsyncRelayCommand SearchCommand { get; }

        public string Keyword
        {
            get => _keyword;
            set => SetProperty(ref _keyword, value);
        }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public OrderLineProductLookupDto? SelectedItem
        {
            get => _selectedItem;
            set => SetProperty(ref _selectedItem, value);
        }

        public async Task InitializeAsync()
        {
            if (!string.IsNullOrWhiteSpace(Keyword))
            {
                await SearchAsync();
            }
        }

        public async Task SearchAsync()
        {
            var route =
                $"{ApiRoutes.Products}?page=1&size=20&is_active=true&q={System.Uri.EscapeDataString(Keyword ?? string.Empty)}";

            IsLoading = true;
            try
            {
                var result = await _apiClient.GetAsync<OrderLineProductListResponse>(route);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "품목 검색 중 오류가 발생했습니다.");
                    return;
                }

                Items.Clear();
                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }
            }
            finally
            {
                IsLoading = false;
            }
        }
    }
}