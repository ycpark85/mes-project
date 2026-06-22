using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using Mes.Wpf.Modules.InspectionSchedules.Views;

namespace Mes.Wpf.Modules.InspectionSchedules.ViewModels
{
    public class InspectionResultManagementPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly bool _canWriteInspection;

        private bool _isLoading;
        private DateTime? _dateFrom = DateTime.Today.AddMonths(-1);
        private DateTime? _dateTo = DateTime.Today;
        private string _searchKeyword = string.Empty;
        private InspectionResultManagementItemDto? _selectedItem;
        private int _totalCount;
        private int _totalGoodQty;
        private int _totalResultShipQty;
        private int _totalDiscardQty;
        private int _totalStockInQty;
        private int _totalDefectQty;

        public InspectionResultManagementPageViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            bool canWriteInspection)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _canWriteInspection = canWriteInspection;

            Items = new ObservableCollection<InspectionResultManagementItemDto>();

            RefreshCommand = new AsyncRelayCommand(LoadAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
            OpenDetailCommand = new AsyncRelayCommand(OpenDetailAsync, () => !IsLoading && SelectedItem != null);
        }

        public ObservableCollection<InspectionResultManagementItemDto> Items { get; }

        public ICommand RefreshCommand { get; }
        public ICommand ResetCommand { get; }
        public ICommand OpenDetailCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (SetProperty(ref _isLoading, value))
                {
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

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public InspectionResultManagementItemDto? SelectedItem
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

        public int TotalCount
        {
            get => _totalCount;
            set => SetProperty(ref _totalCount, value);
        }

        public int TotalGoodQty
        {
            get => _totalGoodQty;
            set => SetProperty(ref _totalGoodQty, value);
        }

        public int TotalResultShipQty
        {
            get => _totalResultShipQty;
            set => SetProperty(ref _totalResultShipQty, value);
        }

        public int TotalDiscardQty
        {
            get => _totalDiscardQty;
            set => SetProperty(ref _totalDiscardQty, value);
        }

        public int TotalStockInQty
        {
            get => _totalStockInQty;
            set => SetProperty(ref _totalStockInQty, value);
        }

        public int TotalDefectQty
        {
            get => _totalDefectQty;
            set => SetProperty(ref _totalDefectQty, value);
        }

        public async Task InitializeAsync()
        {
            await LoadAsync();
        }

        public async Task LoadAsync()
        {
            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<List<InspectionResultManagementItemDto>>(BuildListUrl());
                if (!result.Success || result.Data == null)
                {
                    Items.Clear();
                    SelectedItem = null;
                    UpdateTotals();
                    _messageService.ShowError(result.Message ?? "검수실적 목록 조회에 실패했습니다.");
                    return;
                }

                var selectedId = SelectedItem?.InspectionResultId;

                Items.Clear();
                var rowNo = 1;
                foreach (var item in result.Data)
                {
                    item.RowNo = rowNo++;
                    Items.Add(item);
                }

                SelectedItem = selectedId.HasValue
                    ? Items.FirstOrDefault(x => x.InspectionResultId == selectedId.Value)
                    : null;

                UpdateTotals();
            }
            finally
            {
                IsLoading = false;
            }
        }

        public Task ResetAsync()
        {
            DateFrom = DateTime.Today.AddMonths(-1);
            DateTo = DateTime.Today;
            SearchKeyword = string.Empty;
            SelectedItem = null;

            return LoadAsync();
        }

        public async Task OpenDetailAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("검수실적을 선택해주세요.");
                return;
            }

            var windowVm = new InspectionResultWindowViewModel(
                _apiClient,
                _messageService,
                _canWriteInspection);
            await windowVm.InitializeAsync(
                SelectedItem.InspectionScheduleId,
                SelectedItem.LotNo,
                SelectedItem.ProductName,
                SelectedItem.PartnerName,
                SelectedItem.InspectionDate,
                SelectedItem.LotQty,
                SelectedItem.DueDate,
                SelectedItem.OrderQty);

            var window = new InspectionResultWindow(windowVm)
            {
                Owner = Application.Current?.MainWindow,
                Title = "검수실적 상세보기"
            };

            var dialogResult = window.ShowDialog();
            if (dialogResult == true)
            {
                await LoadAsync();
            }
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string>();

            if (DateFrom.HasValue)
            {
                queryParts.Add($"date_from={DateFrom.Value:yyyy-MM-dd}");
            }

            if (DateTo.HasValue)
            {
                queryParts.Add($"date_to={DateTo.Value:yyyy-MM-dd}");
            }

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }

            return queryParts.Count == 0
                ? ApiRoutes.InspectionResults
                : $"{ApiRoutes.InspectionResults}?{string.Join("&", queryParts)}";
        }

        private void UpdateTotals()
        {
            TotalCount = Items.Count;
            TotalGoodQty = Items.Sum(x => x.GoodQty);
            TotalResultShipQty = Items.Sum(x => x.ResultShipQty);
            TotalDiscardQty = Items.Sum(x => x.DiscardQty);
            TotalStockInQty = Items.Sum(x => x.StockInQty);
            TotalDefectQty = Items.Sum(x => x.DefectQty);
        }

        private void RaiseCommandCanExecuteChanged()
        {
            if (RefreshCommand is AsyncRelayCommand refreshCommand)
            {
                refreshCommand.RaiseCanExecuteChanged();
            }

            if (ResetCommand is AsyncRelayCommand resetCommand)
            {
                resetCommand.RaiseCanExecuteChanged();
            }

            if (OpenDetailCommand is AsyncRelayCommand openDetailCommand)
            {
                openDetailCommand.RaiseCanExecuteChanged();
            }
        }
    }
}
