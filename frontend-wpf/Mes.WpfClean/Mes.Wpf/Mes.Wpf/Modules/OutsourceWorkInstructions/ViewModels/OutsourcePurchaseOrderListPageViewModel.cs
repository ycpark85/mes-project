using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using Microsoft.Win32;
using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels
{
    public class OutsourcePurchaseOrderListPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private DateTime? _dateFrom = DateTime.Today.AddMonths(-1);
        private DateTime? _dateTo = DateTime.Today;
        private string _selectedProcessType = "전체";
        private string _searchKeyword = string.Empty;
        private OutsourcePurchaseOrderListItemDto? _selectedItem;

        public OutsourcePurchaseOrderListPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<OutsourcePurchaseOrderListItemDto>();
            ProcessTypeOptions = new ObservableCollection<string> { "전체", "CUT", "PRINT" };

            SearchCommand = new AsyncRelayCommand(SearchAsync);
            ResetCommand = new RelayCommand(Reset);
            DownloadCommand = new AsyncRelayCommand(DownloadAsync);
        }

        public ObservableCollection<OutsourcePurchaseOrderListItemDto> Items { get; }
        public ObservableCollection<string> ProcessTypeOptions { get; }

        public AsyncRelayCommand SearchCommand { get; }
        public RelayCommand ResetCommand { get; }
        public AsyncRelayCommand DownloadCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public DateTime? DateFrom
        {
            get => _dateFrom;
            set => SetProperty(ref _dateFrom, value);
        }

        public DateTime? DateTo
        {
            get => _dateTo;
            set => SetProperty(ref _dateTo, value);
        }

        public string SelectedProcessType
        {
            get => _selectedProcessType;
            set => SetProperty(ref _selectedProcessType, value);
        }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public OutsourcePurchaseOrderListItemDto? SelectedItem
        {
            get => _selectedItem;
            set => SetProperty(ref _selectedItem, value);
        }

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            IsLoading = true;
            try
            {
                var route = BuildListUrl();
                var result = await _apiClient.GetAsync<OutsourcePurchaseOrderListDto>(route);

                if (result == null || !result.Success || result.Data == null)
                {
                    Items.Clear();
                    _messageService.ShowError(result?.Message ?? "외주발주 목록 조회 중 오류가 발생했습니다.");
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

        private void Reset()
        {
            DateFrom = DateTime.Today.AddMonths(-1);
            DateTo = DateTime.Today;
            SelectedProcessType = "전체";
            SearchKeyword = string.Empty;
            SelectedItem = null;
            _ = SearchAsync();
        }

        private async Task DownloadAsync()
        {
            var target = SelectedItem;
            if (target == null)
            {
                _messageService.ShowWarning("다운로드할 외주발주를 선택하세요.");
                return;
            }

            var route = $"{ApiRoutes.OutsourcePurchaseOrderExcel}/{target.OutsourcePurchaseOrderId}/excel";
            var fileBytes = await _apiClient.GetBytesAsync(route);

            if (fileBytes == null || fileBytes.Length == 0)
            {
                _messageService.ShowWarning("엑셀 다운로드에 실패했습니다.");
                return;
            }

            var dialog = new SaveFileDialog
            {
                FileName = $"{target.PurchaseOrderNo}.xlsx",
                Filter = "Excel Workbook (*.xlsx)|*.xlsx",
                DefaultExt = ".xlsx",
                AddExtension = true,
                OverwritePrompt = true
            };

            if (dialog.ShowDialog() != true)
            {
                return;
            }

            await File.WriteAllBytesAsync(dialog.FileName, fileBytes);
            _messageService.ShowInfo("다운로드되었습니다.");
        }

        private string BuildListUrl()
        {
            var query = new System.Collections.Generic.List<string>();

            if (DateFrom.HasValue)
            {
                query.Add($"date_from={DateFrom.Value:yyyy-MM-dd}");
            }

            if (DateTo.HasValue)
            {
                query.Add($"date_to={DateTo.Value:yyyy-MM-dd}");
            }

            if (!string.IsNullOrWhiteSpace(SelectedProcessType) && SelectedProcessType != "전체")
            {
                query.Add($"process_type={Uri.EscapeDataString(SelectedProcessType.Trim())}");
            }

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }

            return query.Count > 0
                ? $"{ApiRoutes.OutsourcePurchaseOrders}?{string.Join("&", query)}"
                : ApiRoutes.OutsourcePurchaseOrders;
        }
    }
}