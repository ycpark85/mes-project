using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.BohyunOutsourceManagement.Dtos;
using Mes.Wpf.Modules.BohyunOutsourceManagement.Views;

namespace Mes.Wpf.Modules.BohyunOutsourceManagement.ViewModels
{
    public class BohyunOutsourceShipmentListViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private DateTime? _dateFrom;
        private DateTime? _dateTo;
        private string _selectedProcessType = "전체";
        private string _searchKeyword = string.Empty;
        private BohyunOutsourceRowModel? _selectedItem;
        private int _totalCount;
        private decimal _totalOutsourceProcessingFee;

        public BohyunOutsourceShipmentListViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<BohyunOutsourceRowModel>();

            ProcessTypeOptions = new ObservableCollection<string>
            {
                "전체",
                "CUT",
                "PRINT"
            };

            SearchCommand = new AsyncRelayCommand(SearchAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
            PrintCommand = new AsyncRelayCommand(PrintAsync, () => !IsLoading && Items.Count > 0);
        }

        public ObservableCollection<BohyunOutsourceRowModel> Items { get; }

        public ObservableCollection<string> ProcessTypeOptions { get; }

        public ICommand SearchCommand { get; }

        public ICommand ResetCommand { get; }

        public ICommand PrintCommand { get; }

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

        public BohyunOutsourceRowModel? SelectedItem
        {
            get => _selectedItem;
            set => SetProperty(ref _selectedItem, value);
        }

        public int TotalCount
        {
            get => _totalCount;
            set => SetProperty(ref _totalCount, value);
        }

        public decimal TotalOutsourceProcessingFee
        {
            get => _totalOutsourceProcessingFee;
            set => SetProperty(ref _totalOutsourceProcessingFee, value);
        }

        public async Task InitializeAsync()
        {
            DateFrom = DateTime.Today.AddMonths(-1);
            DateTo = DateTime.Today;

            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<BohyunOutsourceListDto>(BuildListUrl());

                if (!result.Success || result.Data == null)
                {
                    Items.Clear();
                    SelectedItem = null;
                    TotalCount = 0;
                    TotalOutsourceProcessingFee = 0;

                    _messageService.ShowError(result.Message ?? "보현문화 출고리스트 조회에 실패했습니다.");
                    return;
                }

                Items.Clear();

                foreach (var item in result.Data.Items)
                {
                    Items.Add(BohyunOutsourceRowModel.FromDto(item));
                }

                SelectedItem = null;
                TotalCount = result.Data.TotalCount;
                RefreshSummary();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task ResetAsync()
        {
            DateFrom = DateTime.Today.AddMonths(-1);
            DateTo = DateTime.Today;
            SelectedProcessType = "전체";
            SearchKeyword = string.Empty;
            SelectedItem = null;

            await SearchAsync();
        }

        private Task PrintAsync()
        {
            if (Items.Count == 0)
            {
                _messageService.ShowWarning("미리보기할 출고 내역이 없습니다.");
                return Task.CompletedTask;
            }

            var document = BuildPrintDocument();

            document.PageWidth = 1122;   // A4 landscape width, 96 DPI 기준
            document.PageHeight = 793;   // A4 landscape height, 96 DPI 기준
            document.PagePadding = new Thickness(24);
            document.ColumnWidth = 1074;

            var previewWindow = new BohyunOutsourceShipmentPrintPreviewWindow(document)
            {
                Owner = Application.Current.MainWindow
            };

            previewWindow.ShowDialog();

            return Task.CompletedTask;
        }

        private FlowDocument BuildPrintDocument()
        {
            var document = new FlowDocument
            {
                FontFamily = new FontFamily("Malgun Gothic"),
                FontSize = 11
            };

            var title = new Paragraph(new Run("보현문화 출고리스트"))
            {
                FontSize = 20,
                FontWeight = FontWeights.Bold,
                TextAlignment = TextAlignment.Center,
                Margin = new Thickness(0, 0, 0, 16)
            };

            document.Blocks.Add(title);

            var conditionText =
                $"조회기간: {DateFrom:yyyy-MM-dd} ~ {DateTo:yyyy-MM-dd}    " +
                $"공정구분: {SelectedProcessType}    " +
                $"검색어: {SearchKeyword}";

            document.Blocks.Add(new Paragraph(new Run(conditionText))
            {
                Margin = new Thickness(0, 0, 0, 6)
            });

            document.Blocks.Add(new Paragraph(new Run(
                $"총 건수: {TotalCount:N0}건    외주가공비 합계: {TotalOutsourceProcessingFee:N0}"))
            {
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 0, 0, 12)
            });

            var table = new Table
            {
                CellSpacing = 0
            };

            table.Columns.Add(new TableColumn { Width = new GridLength(90) });
            table.Columns.Add(new TableColumn { Width = new GridLength(110) });
            table.Columns.Add(new TableColumn { Width = new GridLength(70) });
            table.Columns.Add(new TableColumn { Width = new GridLength(80) });
            table.Columns.Add(new TableColumn { Width = new GridLength(140) });
            table.Columns.Add(new TableColumn { Width = new GridLength(180) });
            table.Columns.Add(new TableColumn { Width = new GridLength(80) });
            table.Columns.Add(new TableColumn { Width = new GridLength(80) });
            table.Columns.Add(new TableColumn { Width = new GridLength(100) });
            table.Columns.Add(new TableColumn { Width = new GridLength(120) });

            var rowGroup = new TableRowGroup();
            table.RowGroups.Add(rowGroup);

            var header = new TableRow();
            rowGroup.Rows.Add(header);

            AddHeaderCell(header, "작업일자");
            AddHeaderCell(header, "작업지시번호");
            AddHeaderCell(header, "공정");
            AddHeaderCell(header, "작업구분");
            AddHeaderCell(header, "거래처명");
            AddHeaderCell(header, "품목명");
            AddHeaderCell(header, "발주시트");
            AddHeaderCell(header, "완료시트");
            AddHeaderCell(header, "외주가공비");
            AddHeaderCell(header, "출고일시");

            foreach (var item in Items)
            {
                var row = new TableRow();
                rowGroup.Rows.Add(row);

                AddBodyCell(row, item.InstructionDate?.ToString("yyyy-MM-dd") ?? string.Empty);
                AddBodyCell(row, item.InstructionNo);
                AddBodyCell(row, item.ProcessTypeName);
                AddBodyCell(row, item.WorkTypeName);
                AddBodyCell(row, item.PartnerName);
                AddBodyCell(row, item.ProductNamesText);
                AddBodyCell(row, item.SheetQty.ToString("N0"));
                AddBodyCell(row, item.WorkDoneSheetQty?.ToString("N0") ?? string.Empty);
                AddBodyCell(row, item.OutsourceProcessingFee?.ToString("N0") ?? string.Empty);
                AddBodyCell(row, item.ShippedAt?.ToString("yyyy-MM-dd HH:mm") ?? string.Empty);
            }

            document.Blocks.Add(table);

            return document;
        }

        private static void AddHeaderCell(TableRow row, string text)
        {
            row.Cells.Add(new TableCell(new Paragraph(new Run(text)))
            {
                FontWeight = FontWeights.Bold,
                Background = Brushes.LightGray,
                BorderBrush = Brushes.Gray,
                BorderThickness = new Thickness(0.5),
                Padding = new Thickness(4),
                TextAlignment = TextAlignment.Center
            });
        }

        private static void AddBodyCell(TableRow row, string text)
        {
            row.Cells.Add(new TableCell(new Paragraph(new Run(text)))
            {
                BorderBrush = Brushes.Gray,
                BorderThickness = new Thickness(0.5),
                Padding = new Thickness(4),
                TextAlignment = TextAlignment.Center
            });
        }

        private void RefreshSummary()
        {
            TotalOutsourceProcessingFee = Items
                .Where(x => x.OutsourceProcessingFee.HasValue)
                .Sum(x => x.OutsourceProcessingFee!.Value);
        }

        private string BuildListUrl()
        {
            NormalizeSearchConditions();

            var queryParts = new List<string>
            {
                "status=SHIPPED"
            };

            if (DateFrom.HasValue)
            {
                queryParts.Add($"date_from={DateFrom.Value:yyyy-MM-dd}");
            }

            if (DateTo.HasValue)
            {
                queryParts.Add($"date_to={DateTo.Value:yyyy-MM-dd}");
            }

            if (!string.IsNullOrWhiteSpace(SelectedProcessType) && SelectedProcessType != "전체")
            {
                queryParts.Add($"process_type={Uri.EscapeDataString(SelectedProcessType)}");
            }

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword)}");
            }

            return $"{ApiRoutes.BohyunOutsourceGroups}?{string.Join("&", queryParts)}";
        }

        private void NormalizeSearchConditions()
        {
            SearchKeyword = SearchKeyword?.Trim() ?? string.Empty;
            SelectedProcessType = SelectedProcessType?.Trim().ToUpperInvariant() ?? "전체";
        }

        private void RaiseCommandCanExecuteChanged()
        {
            if (SearchCommand is AsyncRelayCommand searchCommand)
            {
                searchCommand.RaiseCanExecuteChanged();
            }

            if (ResetCommand is AsyncRelayCommand resetCommand)
            {
                resetCommand.RaiseCanExecuteChanged();
            }

            if (PrintCommand is AsyncRelayCommand printCommand)
            {
                printCommand.RaiseCanExecuteChanged();
            }
        }
    }
}
