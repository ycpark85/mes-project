using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Core.Models;
using Mes.Wpf.Modules.Drawings.Dtos;
using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Drawings.ViewModels
{
    public class DrawingLookupWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _keyword = string.Empty;
        private bool _isLoading;
        private DrawingDto? _selectedItem;

        public DrawingLookupWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            string? initialKeyword = null)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<DrawingDto>();
            SearchCommand = new AsyncRelayCommand(SearchAsync);

            Keyword = initialKeyword?.Trim() ?? string.Empty;
        }

        public ObservableCollection<DrawingDto> Items { get; }

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

        public DrawingDto? SelectedItem
        {
            get => _selectedItem;
            set => SetProperty(ref _selectedItem, value);
        }

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        public async Task SearchAsync()
        {
            var keyword = Keyword?.Trim() ?? string.Empty;

            var route =
                $"{ApiRoutes.Drawings}?page=1&size=50&is_active=true&q={Uri.EscapeDataString(keyword)}";

            IsLoading = true;

            try
            {
                var result = await _apiClient.GetAsync<PagedResult<DrawingDto>>(route);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "도면 검색 중 오류가 발생했습니다.");
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