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
        private int _page = 1;
        private int _pageSize = 100;
        private int _totalCount;

        public OutsourcePurchaseOrderListPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<OutsourcePurchaseOrderListItemDto>();
            ProcessTypeOptions = new ObservableCollection<string> { "전체", "CUT", "PRINT" };

            SearchCommand = new AsyncRelayCommand(SearchFromFirstPageAsync, () => !IsLoading);
            ResetCommand = new RelayCommand(Reset);
            PreviousPageCommand = new AsyncRelayCommand(PreviousPageAsync, () => CanGoPrevious);
            NextPageCommand = new AsyncRelayCommand(NextPageAsync, () => CanGoNext);
            DownloadCommand = new AsyncRelayCommand(
                DownloadAsync,
                parameter => !IsLoading && (parameter is OutsourcePurchaseOrderListItemDto || SelectedItem != null));
        }

        public ObservableCollection<OutsourcePurchaseOrderListItemDto> Items { get; }
        public ObservableCollection<string> ProcessTypeOptions { get; }

        public AsyncRelayCommand SearchCommand { get; }
        public RelayCommand ResetCommand { get; }
        public AsyncRelayCommand PreviousPageCommand { get; }
        public AsyncRelayCommand NextPageCommand { get; }
        public AsyncRelayCommand DownloadCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (SetProperty(ref _isLoading, value))
                {
                    RaisePagingStateChanged();
                    RaiseCommandCanExecuteChanged();
                }
            }
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
            set
            {
                if (SetProperty(ref _selectedItem, value))
                {
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public int Page
        {
            get => _page;
            set
            {
                var normalized = Math.Max(1, value);
                if (SetProperty(ref _page, normalized))
                {
                    RaisePagingStateChanged();
                }
            }
        }

        public int PageSize
        {
            get => _pageSize;
            set
            {
                var normalized = Math.Max(1, value);
                if (SetProperty(ref _pageSize, normalized))
                {
                    RaisePagingStateChanged();
                }
            }
        }

        public int TotalCount
        {
            get => _totalCount;
            set
            {
                var normalized = Math.Max(0, value);
                if (SetProperty(ref _totalCount, normalized))
                {
                    RaisePagingStateChanged();
                }
            }
        }

        public int TotalPages => Math.Max(1, (int)Math.Ceiling(TotalCount / (double)Math.Max(1, PageSize)));

        public string PageInfo => $"{TotalCount:N0}건 / {Page:N0} / {TotalPages:N0} 페이지";

        public bool CanGoPrevious => !IsLoading && Page > 1;

        public bool CanGoNext => !IsLoading && Page < TotalPages;

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        private async Task SearchFromFirstPageAsync()
        {
            Page = 1;
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
                    TotalCount = 0;
                    _messageService.ShowError(result?.Message ?? "외주발주 목록 조회 중 오류가 발생했습니다.");
                    return;
                }

                TotalCount = result.Data.TotalCount;
                Page = result.Data.Page;
                PageSize = result.Data.Size;

                Items.Clear();
                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }

                SelectedItem = Items.Count > 0 ? Items[0] : null;
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
            Page = 1;
            _ = SearchAsync();
        }

        private async Task PreviousPageAsync()
        {
            if (!CanGoPrevious)
            {
                return;
            }

            Page--;
            await SearchAsync();
        }

        private async Task NextPageAsync()
        {
            if (!CanGoNext)
            {
                return;
            }

            Page++;
            await SearchAsync();
        }

        private async Task DownloadAsync(object? parameter)
        {
            var target = parameter as OutsourcePurchaseOrderListItemDto ?? SelectedItem;

            if (target == null)
            {
                _messageService.ShowWarning("다운로드할 외주발주를 선택하세요.");
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

            try
            {
                IsLoading = true;

                var route = $"{ApiRoutes.OutsourcePurchaseOrderExcel}/{target.OutsourcePurchaseOrderId}/excel";
                var download = await _apiClient.DownloadFileAsync(route, dialog.FileName);

                if (!download.Success)
                {
                    _messageService.ShowWarning(download.Message ?? "엑셀 다운로드에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("다운로드되었습니다.");
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildListUrl()
        {
            var query = new System.Collections.Generic.List<string>();

            query.Add($"page={Page}");
            query.Add($"size={PageSize}");

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

        private void RaisePagingStateChanged()
        {
            OnPropertyChanged(nameof(TotalPages));
            OnPropertyChanged(nameof(PageInfo));
            OnPropertyChanged(nameof(CanGoPrevious));
            OnPropertyChanged(nameof(CanGoNext));
            RaiseCommandCanExecuteChanged();
        }

        private void RaiseCommandCanExecuteChanged()
        {
            SearchCommand.RaiseCanExecuteChanged();
            PreviousPageCommand.RaiseCanExecuteChanged();
            NextPageCommand.RaiseCanExecuteChanged();
            DownloadCommand.RaiseCanExecuteChanged();
        }
    }
}
