using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OrderLines.Dtos;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Partners.ViewModels
{
    public class PartnerLookupWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _keyword = string.Empty;
        private bool _isLoading;
        private OrderLinePartnerLookupDto? _selectedItem;

        public PartnerLookupWindowViewModel(IApiClient apiClient, IMessageService messageService, string? initialKeyword = null)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<OrderLinePartnerLookupDto>();
            SearchCommand = new AsyncRelayCommand(SearchAsync);

            Keyword = initialKeyword?.Trim() ?? string.Empty;
        }

        public ObservableCollection<OrderLinePartnerLookupDto> Items { get; }
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

        public OrderLinePartnerLookupDto? SelectedItem
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
            var route = $"{ApiRoutes.Partners}?page=1&size=20&is_active=true&q={Uri.EscapeDataString(Keyword ?? string.Empty)}";
            IsLoading = true;
            try
            {
                var result = await _apiClient.GetAsync<OrderLinePartnerListResponse>(route);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "거래처 검색 중 오류가 발생했습니다.");
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