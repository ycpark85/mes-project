using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.InspectionSchedules.ViewModels
{
    public class DefectTypeLookupWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private readonly Dictionary<string, List<InspectionResultDefectTypeLookupDto>> _cache
            = new(StringComparer.OrdinalIgnoreCase);

        private string _keyword = string.Empty;
        private string _selectedUseYn = "사용";
        private bool _isLoading;
        private InspectionResultDefectTypeLookupDto? _selectedItem;

        public DefectTypeLookupWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            string? initialKeyword = null)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<InspectionResultDefectTypeLookupDto>();
            UseYnOptions = new ObservableCollection<string>
            {
                "사용",
                "미사용"
            };

            SearchCommand = new AsyncRelayCommand(SearchAsync);

            Keyword = initialKeyword?.Trim() ?? string.Empty;
        }

        public ObservableCollection<InspectionResultDefectTypeLookupDto> Items { get; }

        public ObservableCollection<string> UseYnOptions { get; }

        public AsyncRelayCommand SearchCommand { get; }

        public string Keyword
        {
            get => _keyword;
            set => SetProperty(ref _keyword, value);
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

        public InspectionResultDefectTypeLookupDto? SelectedItem
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
            var normalizedKeyword = (Keyword ?? string.Empty).Trim();
            var cacheKey = $"{SelectedUseYn}|{normalizedKeyword.ToUpperInvariant()}";

            if (_cache.TryGetValue(cacheKey, out var cachedItems))
            {
                BindItems(cachedItems);
                return;
            }

            var route = BuildListUrl(normalizedKeyword);

            IsLoading = true;

            try
            {
                var result = await _apiClient.GetAsync<InspectionResultDefectTypeLookupResponse>(route);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "불량유형 조회 중 오류가 발생했습니다.");
                    return;
                }

                var items = result.Data?.Items ?? new List<InspectionResultDefectTypeLookupDto>();

                _cache[cacheKey] = new List<InspectionResultDefectTypeLookupDto>(items);
                BindItems(items);
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildListUrl(string keyword)
        {
            var queryParts = new List<string>
            {
                "page=1",
                "size=100"
            };

            if (!string.IsNullOrWhiteSpace(keyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(keyword)}");
            }

            if (SelectedUseYn == "사용")
            {
                queryParts.Add("is_active=true");
            }
            else if (SelectedUseYn == "미사용")
            {
                queryParts.Add("is_active=false");
            }

            return $"{ApiRoutes.DefectTypes}?{string.Join("&", queryParts)}";
        }

        private void BindItems(IEnumerable<InspectionResultDefectTypeLookupDto> items)
        {
            Items.Clear();

            foreach (var item in items)
            {
                Items.Add(item);
            }

            SelectedItem = null;
        }
    }
}