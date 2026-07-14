using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using Mes.Vendor.Wpf.Core;
using Mes.Vendor.Wpf.Dtos;
using Mes.Vendor.Wpf.Infrastructure;
using Mes.Vendor.Wpf.Views;

namespace Mes.Vendor.Wpf.ViewModels;

public sealed class MainViewModel : BindableBase
{
    private const string VendorBohyunGroupsRoute = "api/v1/vendor-portal/bohyun-groups";
    private static readonly Brush SelectedMenuBrush = new SolidColorBrush(Color.FromRgb(13, 111, 211));

    private readonly ApiClient _apiClient;
    private readonly MessageService _messages;
    private readonly AuthLoginResponse _loginResponse;
    private DateTime? _dateFrom = DateTime.Today.AddMonths(-1);
    private DateTime? _dateTo = DateTime.Today;
    private OptionItem? _selectedProcessType;
    private OptionItem? _selectedStatus;
    private string _searchText = string.Empty;
    private string _statusMessage = string.Empty;
    private bool _isLoading;
    private BohyunOutsourceRow? _selectedItem;
    private int _totalCount;
    private int _currentPage = 1;
    private int _pageSize = 100;
    private decimal _totalOutsourceProcessingFee;
    private VendorMenuMode _activeMenu = VendorMenuMode.OutsourceManagement;

    public MainViewModel(ApiClient apiClient, MessageService messages, AuthLoginResponse loginResponse)
    {
        _apiClient = apiClient;
        _messages = messages;
        _loginResponse = loginResponse;

        ProcessTypes = new ObservableCollection<OptionItem>
        {
            new("전체", null),
            new("재단", "CUT"),
            new("인쇄", "PRINT"),
            new("도무송", "DIECUT")
        };

        Statuses = new ObservableCollection<OptionItem>
        {
            new("전체", null),
            new("입고대기", "WAITING_INBOUND"),
            new("입고완료", "INBOUNDED"),
            new("작업완료", "WORK_DONE"),
            new("출고완료", "SHIPPED")
        };

        SelectedProcessType = ProcessTypes[0];
        SelectedStatus = Statuses[0];

        SearchCommand = new AsyncRelayCommand(SearchAsync, () => !IsLoading);
        ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
        PreviousPageCommand = new AsyncRelayCommand(GoPreviousPageAsync, () => !IsLoading && HasPreviousPage);
        NextPageCommand = new AsyncRelayCommand(GoNextPageAsync, () => !IsLoading && HasNextPage);
        InboundCommand = new AsyncRelayCommand(InboundAsync, CanInbound);
        WorkDoneCommand = new AsyncRelayCommand(WorkDoneAsync, CanWorkDone);
        ShipSelectedCommand = new AsyncRelayCommand(ShipSelectedAsync, CanShipSelected);
        PrintCommand = new AsyncRelayCommand(PrintShipmentListAsync, () => !IsLoading && ActiveMenu == VendorMenuMode.ShipmentManagement && TotalCount > 0);
        OpenOutsourceManagementCommand = new AsyncRelayCommand(() => ChangeMenuAsync(VendorMenuMode.OutsourceManagement), () => !IsLoading);
        OpenShipmentManagementCommand = new AsyncRelayCommand(() => ChangeMenuAsync(VendorMenuMode.ShipmentManagement), () => !IsLoading);
        LogoutCommand = new RelayCommand(_ => RequestLogout?.Invoke(this, EventArgs.Empty));
    }

    public event EventHandler? RequestLogout;

    public ObservableCollection<BohyunOutsourceRow> Items { get; } = new();
    public ObservableCollection<OptionItem> ProcessTypes { get; }
    public ObservableCollection<OptionItem> Statuses { get; }

    public ICommand SearchCommand { get; }
    public ICommand ResetCommand { get; }
    public ICommand PreviousPageCommand { get; }
    public ICommand NextPageCommand { get; }
    public ICommand InboundCommand { get; }
    public ICommand WorkDoneCommand { get; }
    public ICommand ShipSelectedCommand { get; }
    public ICommand PrintCommand { get; }
    public ICommand OpenOutsourceManagementCommand { get; }
    public ICommand OpenShipmentManagementCommand { get; }
    public ICommand LogoutCommand { get; }

    public string UserDisplayName => _loginResponse.User?.UserName ?? _loginResponse.User?.LoginId ?? "외주업체";
    public string HeaderTitle => ActiveMenu == VendorMenuMode.ShipmentManagement ? "보현문화 출고리스트" : "보현문화 외주관리";
    public string HeaderSubtitle => ActiveMenu == VendorMenuMode.ShipmentManagement
        ? "보현문화 출고완료 내역 확인"
        : "보현문화 입고 / 작업완료 / 출고 처리";
    public string ListTitle => ActiveMenu == VendorMenuMode.ShipmentManagement ? "출고 리스트" : "작업 목록";
    public string ListHeaderText => $"{ListTitle} ({TotalCount:N0}건)";
    public Visibility WorkManagementFilterVisibility => Visibility.Visible;
    public Visibility StatusFilterVisibility => ActiveMenu == VendorMenuMode.OutsourceManagement ? Visibility.Visible : Visibility.Collapsed;
    public Visibility OutsourceManagementColumnVisibility => ActiveMenu == VendorMenuMode.OutsourceManagement ? Visibility.Visible : Visibility.Collapsed;
    public Visibility ShipmentManagementColumnVisibility => ActiveMenu == VendorMenuMode.ShipmentManagement ? Visibility.Visible : Visibility.Collapsed;
    public Visibility ShipmentSummaryVisibility => ActiveMenu == VendorMenuMode.ShipmentManagement ? Visibility.Visible : Visibility.Collapsed;
    public Visibility WorkActionVisibility => ActiveMenu == VendorMenuMode.OutsourceManagement ? Visibility.Visible : Visibility.Collapsed;
    public Visibility ShipmentActionVisibility => ActiveMenu == VendorMenuMode.ShipmentManagement ? Visibility.Visible : Visibility.Collapsed;
    public Brush OutsourceMenuBackground => ActiveMenu == VendorMenuMode.OutsourceManagement ? SelectedMenuBrush : Brushes.Transparent;
    public Brush ShipmentMenuBackground => ActiveMenu == VendorMenuMode.ShipmentManagement ? SelectedMenuBrush : Brushes.Transparent;

    public VendorMenuMode ActiveMenu
    {
        get => _activeMenu;
        private set
        {
            if (SetProperty(ref _activeMenu, value))
            {
                OnPropertyChanged(nameof(HeaderTitle));
                OnPropertyChanged(nameof(HeaderSubtitle));
                OnPropertyChanged(nameof(ListTitle));
                OnPropertyChanged(nameof(ListHeaderText));
                OnPropertyChanged(nameof(WorkManagementFilterVisibility));
                OnPropertyChanged(nameof(StatusFilterVisibility));
                OnPropertyChanged(nameof(OutsourceManagementColumnVisibility));
                OnPropertyChanged(nameof(ShipmentManagementColumnVisibility));
                OnPropertyChanged(nameof(ShipmentSummaryVisibility));
                OnPropertyChanged(nameof(WorkActionVisibility));
                OnPropertyChanged(nameof(ShipmentActionVisibility));
                OnPropertyChanged(nameof(OutsourceMenuBackground));
                OnPropertyChanged(nameof(ShipmentMenuBackground));
                RaiseCommandStatesChanged();
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

    public OptionItem? SelectedProcessType
    {
        get => _selectedProcessType;
        set => SetProperty(ref _selectedProcessType, value);
    }

    public OptionItem? SelectedStatus
    {
        get => _selectedStatus;
        set => SetProperty(ref _selectedStatus, value);
    }

    public string SearchText
    {
        get => _searchText;
        set => SetProperty(ref _searchText, value);
    }

    public bool IsLoading
    {
        get => _isLoading;
        private set
        {
            if (SetProperty(ref _isLoading, value))
            {
                RaiseCommandStatesChanged();
            }
        }
    }

    public string StatusMessage
    {
        get => _statusMessage;
        private set => SetProperty(ref _statusMessage, value);
    }

    public BohyunOutsourceRow? SelectedItem
    {
        get => _selectedItem;
        set
        {
            if (SetProperty(ref _selectedItem, value))
            {
                RaiseCommandStatesChanged();
            }
        }
    }

    public int TotalCount
    {
        get => _totalCount;
        private set
        {
            if (SetProperty(ref _totalCount, value))
            {
                OnPropertyChanged(nameof(ListHeaderText));
                RaisePagePropertiesChanged();
            }
        }
    }

    public int CurrentPage
    {
        get => _currentPage;
        private set
        {
            if (SetProperty(ref _currentPage, value))
            {
                RaisePagePropertiesChanged();
            }
        }
    }

    public int PageSize
    {
        get => _pageSize;
        private set
        {
            if (SetProperty(ref _pageSize, value))
            {
                RaisePagePropertiesChanged();
            }
        }
    }

    public int TotalPages => Math.Max(1, (int)Math.Ceiling(TotalCount / (double)Math.Max(PageSize, 1)));
    public bool HasPreviousPage => CurrentPage > 1;
    public bool HasNextPage => CurrentPage < TotalPages;
    public string PageDisplayText => $"{CurrentPage} / {TotalPages} (총 {TotalCount:N0}건)";

    public decimal TotalOutsourceProcessingFee
    {
        get => _totalOutsourceProcessingFee;
        private set => SetProperty(ref _totalOutsourceProcessingFee, value);
    }

    public async Task InitializeAsync()
    {
        await SearchAsync();
    }

    private async Task ResetAsync()
    {
        DateFrom = DateTime.Today.AddMonths(-1);
        DateTo = DateTime.Today;
        SelectedProcessType = ProcessTypes[0];
        SelectedStatus = ActiveMenu == VendorMenuMode.ShipmentManagement
            ? Statuses.First(status => status.Value == "SHIPPED")
            : Statuses[0];
        SearchText = string.Empty;
        await SearchAsync();
    }

    private async Task ChangeMenuAsync(VendorMenuMode menu)
    {
        if (ActiveMenu == menu)
        {
            return;
        }

        ActiveMenu = menu;
        SelectedStatus = menu == VendorMenuMode.ShipmentManagement
            ? Statuses.First(status => status.Value == "SHIPPED")
            : Statuses[0];
        await SearchAsync();
    }

    private async Task SearchAsync()
    {
        CurrentPage = 1;
        await LoadAsync();
    }

    private async Task LoadAsync()
    {
        if (DateFrom.HasValue && DateTo.HasValue && DateFrom.Value.Date > DateTo.Value.Date)
        {
            _messages.ShowWarning("조회 시작일은 종료일보다 늦을 수 없습니다.");
            return;
        }

        IsLoading = true;
        StatusMessage = "조회 중입니다.";

        try
        {
            var result = await _apiClient.GetAsync<BohyunOutsourceListDto>(BuildListUrl());
            if (!result.Success || result.Data is null)
            {
                StatusMessage = "조회 실패";
                _messages.ShowError(result.Message ?? "외주 작업 목록을 조회하지 못했습니다.");
                return;
            }

            Items.Clear();
            foreach (var row in result.Data.Items.Select(BohyunOutsourceRow.FromDto))
            {
                row.PropertyChanged += (_, args) =>
                {
                    if (args.PropertyName == nameof(BohyunOutsourceRow.IsChecked))
                    {
                        RaiseCommandStatesChanged();
                    }
                };
                Items.Add(row);
            }

            TotalCount = result.Data.TotalCount;
            CurrentPage = result.Data.Page;
            PageSize = result.Data.Size;
            TotalOutsourceProcessingFee = result.Data.ProcessingFeeTotal;
            SelectedItem = Items.FirstOrDefault();
            RaiseCommandStatesChanged();
            StatusMessage = TotalCount == 0
                ? "조회된 작업이 없습니다."
                : $"{TotalCount:N0}건 조회되었습니다.";
        }
        finally
        {
            IsLoading = false;
        }
    }

    private async Task GoPreviousPageAsync()
    {
        if (!HasPreviousPage)
        {
            return;
        }

        CurrentPage--;
        await LoadAsync();
    }

    private async Task GoNextPageAsync()
    {
        if (!HasNextPage)
        {
            return;
        }

        CurrentPage++;
        await LoadAsync();
    }

    private async Task InboundAsync(object? parameter)
    {
        var target = ResolveTargetItem(parameter);
        if (target is null || !target.CanInbound)
        {
            return;
        }

        SelectedItem = target;

        if (!_messages.Confirm($"작업지시 [{target.InstructionNo}] {target.WorkTypeName} 작업을 입고완료 처리하시겠습니까?"))
        {
            return;
        }

        await PostAndRefreshAsync(
            $"{VendorBohyunGroupsRoute}/{target.OutsourceWorkGroupId}/inbound",
            new { },
            "입고완료 처리되었습니다.",
            "입고 처리에 실패했습니다.");
    }

    private async Task WorkDoneAsync(object? parameter)
    {
        var target = ResolveTargetItem(parameter);
        if (target is null || !target.CanWorkDone)
        {
            return;
        }

        SelectedItem = target;

        var dialog = new WorkDoneWindow(target)
        {
            Owner = App.Current.MainWindow
        };

        if (dialog.ShowDialog() != true)
        {
            return;
        }

        if (!_messages.Confirm("보현문화 작업완료 처리하시겠습니까?"))
        {
            return;
        }

        await PostAndRefreshAsync(
            $"{VendorBohyunGroupsRoute}/{target.OutsourceWorkGroupId}/work-done",
            new BohyunWorkDoneRequest
            {
                WorkDoneSheetQty = dialog.WorkDoneSheetQty,
                OutsourceProcessingFee = dialog.OutsourceProcessingFee,
                Remark = dialog.Remark
            },
            "작업완료 처리되었습니다.",
            "작업완료 처리에 실패했습니다.");
    }

    private async Task ShipSelectedAsync()
    {
        var groupIds = Items
            .Where(item => item.IsChecked && item.CanShip)
            .Select(item => item.OutsourceWorkGroupId)
            .ToList();

        if (groupIds.Count == 0 && SelectedItem?.CanShip == true)
        {
            groupIds.Add(SelectedItem.OutsourceWorkGroupId);
        }

        if (groupIds.Count == 0)
        {
            _messages.ShowWarning("출고 가능한 작업완료 건을 선택해 주세요.");
            return;
        }

        if (!_messages.Confirm($"{groupIds.Count:N0}건을 출고완료 처리하시겠습니까?"))
        {
            return;
        }

        await PostAndRefreshAsync(
            $"{VendorBohyunGroupsRoute}/ship-batch",
            new BohyunShipBatchRequest { GroupIds = groupIds },
            "출고완료 처리되었습니다.",
            "출고 처리에 실패했습니다.");
    }

    private async Task PostAndRefreshAsync<TRequest>(
        string route,
        TRequest request,
        string successMessage,
        string failureMessage)
    {
        IsLoading = true;
        try
        {
            var result = await _apiClient.PostAsync<TRequest, SimpleSuccessResponse>(route, request);
            if (!result.Success)
            {
                _messages.ShowError(result.Message ?? failureMessage);
                return;
            }

            StatusMessage = successMessage;
            await SearchAsync();
        }
        finally
        {
            IsLoading = false;
        }
    }

    private bool CanInbound()
    {
        return !IsLoading && ActiveMenu == VendorMenuMode.OutsourceManagement && SelectedItem?.CanInbound == true;
    }

    private bool CanInbound(object? parameter)
    {
        return !IsLoading
            && ActiveMenu == VendorMenuMode.OutsourceManagement
            && ResolveTargetItem(parameter)?.CanInbound == true;
    }

    private bool CanWorkDone()
    {
        return !IsLoading && ActiveMenu == VendorMenuMode.OutsourceManagement && SelectedItem?.CanWorkDone == true;
    }

    private bool CanWorkDone(object? parameter)
    {
        return !IsLoading
            && ActiveMenu == VendorMenuMode.OutsourceManagement
            && ResolveTargetItem(parameter)?.CanWorkDone == true;
    }

    private bool CanShipSelected()
    {
        return !IsLoading
            && (SelectedItem?.CanShip == true || Items.Any(item => item.IsChecked && item.CanShip));
    }

    private async Task PrintShipmentListAsync()
    {
        if (TotalCount == 0)
        {
            _messages.ShowWarning("미리보기할 출고 내역이 없습니다.");
            return;
        }

        IsLoading = true;
        try
        {
            const int printPageSize = 200;
            var printItems = new List<BohyunOutsourceRow>();
            var page = 1;
            var totalPages = 1;

            do
            {
                var result = await _apiClient.GetAsync<BohyunOutsourceListDto>(
                    BuildListUrl(page, printPageSize));
                if (!result.Success || result.Data is null)
                {
                    _messages.ShowError(result.Message ?? "출고리스트 전체 조회에 실패했습니다.");
                    return;
                }

                printItems.AddRange(result.Data.Items.Select(BohyunOutsourceRow.FromDto));
                totalPages = Math.Max(
                    1,
                    (int)Math.Ceiling(result.Data.TotalCount / (double)printPageSize));
                page++;
            }
            while (page <= totalPages);

            ShowShipmentPrintPreview(printItems);
        }
        finally
        {
            IsLoading = false;
        }
    }

    private void ShowShipmentPrintPreview(IReadOnlyCollection<BohyunOutsourceRow> items)
    {
        var document = BuildShipmentPrintDocument(items);
        document.PageWidth = 1122;
        document.PageHeight = 793;
        document.PagePadding = new Thickness(24);
        document.ColumnWidth = 1074;

        var previewWindow = new ShipmentPrintPreviewWindow(document)
        {
            Owner = App.Current.MainWindow
        };

        previewWindow.ShowDialog();
    }

    private FlowDocument BuildShipmentPrintDocument(IReadOnlyCollection<BohyunOutsourceRow> items)
    {
        var document = new FlowDocument
        {
            FontFamily = new FontFamily("Malgun Gothic"),
            FontSize = 11
        };

        document.Blocks.Add(new Paragraph(new Run("보현문화 출고리스트"))
        {
            FontSize = 20,
            FontWeight = FontWeights.Bold,
            TextAlignment = TextAlignment.Center,
            Margin = new Thickness(0, 0, 0, 16)
        });

        document.Blocks.Add(new Paragraph(new Run(
            $"조회기간: {DateFrom:yyyy-MM-dd} ~ {DateTo:yyyy-MM-dd}    공정구분: {SelectedProcessType}    검색어: {SearchText}"))
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

        foreach (var width in new[] { 90, 110, 70, 80, 140, 180, 80, 80, 100, 120 })
        {
            table.Columns.Add(new TableColumn { Width = new GridLength(width) });
        }

        var rowGroup = new TableRowGroup();
        table.RowGroups.Add(rowGroup);

        var header = new TableRow();
        rowGroup.Rows.Add(header);

        AddPrintCell(header, "작업일자", true);
        AddPrintCell(header, "작업지시번호", true);
        AddPrintCell(header, "공정", true);
        AddPrintCell(header, "작업구분", true);
        AddPrintCell(header, "거래처명", true);
        AddPrintCell(header, "품목명", true);
        AddPrintCell(header, "발주시트", true);
        AddPrintCell(header, "완료시트", true);
        AddPrintCell(header, "외주가공비", true);
        AddPrintCell(header, "출고일시", true);

        foreach (var item in items)
        {
            var row = new TableRow();
            rowGroup.Rows.Add(row);

            AddPrintCell(row, item.InstructionDate?.ToString("yyyy-MM-dd") ?? string.Empty);
            AddPrintCell(row, item.InstructionNo);
            AddPrintCell(row, item.ProcessTypeName);
            AddPrintCell(row, item.WorkTypeName);
            AddPrintCell(row, item.PartnerName);
            AddPrintCell(row, item.ProductNamesText);
            AddPrintCell(row, item.SheetQty.ToString("N0"));
            AddPrintCell(row, item.WorkDoneSheetQty?.ToString("N0") ?? string.Empty);
            AddPrintCell(row, item.OutsourceProcessingFee?.ToString("N0") ?? string.Empty);
            AddPrintCell(row, item.ShippedAt?.ToString("yyyy-MM-dd HH:mm") ?? string.Empty);
        }

        document.Blocks.Add(table);
        return document;
    }

    private static void AddPrintCell(TableRow row, string text, bool isHeader = false)
    {
        row.Cells.Add(new TableCell(new Paragraph(new Run(text)))
        {
            FontWeight = isHeader ? FontWeights.Bold : FontWeights.Normal,
            Background = isHeader ? Brushes.LightGray : Brushes.Transparent,
            BorderBrush = Brushes.Gray,
            BorderThickness = new Thickness(0.5),
            Padding = new Thickness(4),
            TextAlignment = TextAlignment.Center
        });
    }

    private string BuildListUrl(int? page = null, int? size = null)
    {
        var query = new List<string>();

        if (DateFrom.HasValue)
        {
            query.Add($"date_from={DateFrom.Value:yyyy-MM-dd}");
        }

        if (DateTo.HasValue)
        {
            query.Add($"date_to={DateTo.Value:yyyy-MM-dd}");
        }

        if (!string.IsNullOrWhiteSpace(SelectedProcessType?.Value))
        {
            query.Add($"process_type={Uri.EscapeDataString(SelectedProcessType.Value)}");
        }

        if (ActiveMenu == VendorMenuMode.ShipmentManagement)
        {
            query.Add("status=SHIPPED");
        }
        else if (!string.IsNullOrWhiteSpace(SelectedStatus?.Value))
        {
            query.Add($"status={Uri.EscapeDataString(SelectedStatus.Value)}");
        }

        if (!string.IsNullOrWhiteSpace(SearchText))
        {
            query.Add($"q={Uri.EscapeDataString(SearchText.Trim())}");
        }

        query.Add($"page={page ?? CurrentPage}");
        query.Add($"size={size ?? PageSize}");

        return query.Count == 0
            ? VendorBohyunGroupsRoute
            : $"{VendorBohyunGroupsRoute}?{string.Join("&", query)}";
    }

    private BohyunOutsourceRow? ResolveTargetItem(object? parameter)
    {
        return parameter as BohyunOutsourceRow ?? SelectedItem;
    }

    private void RaiseCommandStatesChanged()
    {
        foreach (var command in new[]
                 {
                     SearchCommand,
                     ResetCommand,
                     PreviousPageCommand,
                     NextPageCommand,
                     InboundCommand,
                     WorkDoneCommand,
                     ShipSelectedCommand,
                     PrintCommand,
                     OpenOutsourceManagementCommand,
                     OpenShipmentManagementCommand
                 })
        {
            if (command is AsyncRelayCommand asyncCommand)
            {
                asyncCommand.RaiseCanExecuteChanged();
            }
        }

    }

    private void RaisePagePropertiesChanged()
    {
        OnPropertyChanged(nameof(TotalPages));
        OnPropertyChanged(nameof(HasPreviousPage));
        OnPropertyChanged(nameof(HasNextPage));
        OnPropertyChanged(nameof(PageDisplayText));
        RaiseCommandStatesChanged();
    }
}

public enum VendorMenuMode
{
    OutsourceManagement,
    ShipmentManagement
}

public sealed record OptionItem(string Label, string? Value)
{
    public override string ToString() => Label;
}

public sealed class SimpleSuccessResponse
{
    public bool Success { get; set; }
}
