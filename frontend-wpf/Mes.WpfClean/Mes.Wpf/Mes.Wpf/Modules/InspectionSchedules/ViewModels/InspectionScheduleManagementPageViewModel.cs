using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using System.Windows;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using Mes.Wpf.Modules.InspectionSchedules.Views;
using Mes.Wpf.Modules.LotDetails.ViewModels;
using Mes.Wpf.Modules.LotDetails.Views;
namespace Mes.Wpf.Modules.InspectionSchedules.ViewModels
{
    public class InspectionScheduleManagementPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly IDrawingViewer _drawingViewer;
        private readonly bool _canWriteInspection;

        private bool _isLoading;
        private DateTime? _searchDate = DateTime.Today;
        private string _status = string.Empty;
        private string _partnerQuery = string.Empty;
        private string _productQuery = string.Empty;
        private int _totalCount;
        private int _totalShipQty;
        private InspectionScheduleListItemDto? _selectedItem;
        private bool _isHandlingDateChange;

        public InspectionScheduleManagementPageViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            IDrawingViewer drawingViewer,
            bool canWriteInspection)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _drawingViewer = drawingViewer;
            _canWriteInspection = canWriteInspection;

            Items = new ObservableCollection<InspectionScheduleListItemDto>();
            EditModel = new InspectionScheduleManagementEditModel();

            RefreshCommand = new AsyncRelayCommand(LoadAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
            ClearSelectionCommand = new AsyncRelayCommand(ClearSelectionAsync, () => !IsLoading);

            PrintLabelCommand = new AsyncRelayCommand(
                OpenLabelPrintWindowAsync,
                () => !IsLoading && SelectedItem != null);

            OpenLotDetailCommand = new AsyncRelayCommand(
                OpenLotDetailAsync,
                () => !IsLoading && SelectedItem != null);

            OpenDrawingCommand = new AsyncRelayCommand(
                OpenDrawingAsync,
                () => !IsLoading && SelectedItem != null);

            OpenPlateDataCommand = new AsyncRelayCommand<InspectionScheduleListItemDto>(
                OpenPlateDataAsync,
                item => !IsLoading && item != null && item.HasBundle);

            SelectItemCommand = new AsyncRelayCommand<InspectionScheduleListItemDto>(
                SelectItemAsync,
                item => !IsLoading && item != null);

            ReceiveCommand = new AsyncRelayCommand(
                ReceiveAsync,
                () => !IsLoading && CanReceive());

            StartCommand = new AsyncRelayCommand(
                StartAsync,
                () => !IsLoading && CanStart());

            CancelCommand = new AsyncRelayCommand(
                CancelAsync,
                () => !IsLoading && CanCancel());

            MoveUpCommand = new AsyncRelayCommand(
                MoveUpAsync,
                () => !IsLoading && CanMoveUp());

            MoveDownCommand = new AsyncRelayCommand(
                MoveDownAsync,
                () => !IsLoading && CanMoveDown());



            EditModel.Clear();
        }

        public ObservableCollection<InspectionScheduleListItemDto> Items { get; }

        public InspectionScheduleManagementEditModel EditModel { get; }

        public ICommand RefreshCommand { get; }
        public ICommand ResetCommand { get; }
        public ICommand ClearSelectionCommand { get; }
        public ICommand PrintLabelCommand { get; }
        public ICommand SelectItemCommand { get; }
        public ICommand OpenDrawingCommand { get; }
        public ICommand OpenPlateDataCommand { get; }
        public ICommand OpenLotDetailCommand { get; }
        public ICommand ReceiveCommand { get; }
        public ICommand StartCommand { get; }
        public ICommand CancelCommand { get; }
        public ICommand MoveUpCommand { get; }
        public ICommand MoveDownCommand { get; }

        public bool CanWriteInspection => _canWriteInspection;

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

        public DateTime? SearchDate
        {
            get => _searchDate;
            set => SetProperty(ref _searchDate, value);
        }

        public string Status
        {
            get => _status;
            set => SetProperty(ref _status, value);
        }

        public string PartnerQuery
        {
            get => _partnerQuery;
            set => SetProperty(ref _partnerQuery, value);
        }

        public string ProductQuery
        {
            get => _productQuery;
            set => SetProperty(ref _productQuery, value);
        }

        public int TotalCount
        {
            get => _totalCount;
            set => SetProperty(ref _totalCount, value);
        }

        public int TotalShipQty
        {
            get => _totalShipQty;
            set => SetProperty(ref _totalShipQty, value);
        }

        public InspectionScheduleListItemDto? SelectedItem
        {
            get => _selectedItem;
            set
            {
                if (SetProperty(ref _selectedItem, value))
                {
                    if (value == null)
                    {
                        EditModel.Clear();
                    }
                    else
                    {
                        EditModel.LoadFromDto(value);
                    }

                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        private async Task OpenLotDetailAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("LOT를 선택해주세요.");
                return;
            }

            if (SelectedItem.LotId <= 0)
            {
                _messageService.ShowWarning("LOT 정보가 없습니다.");
                return;
            }

            var windowVm = new LotDetailWindowViewModel(_apiClient, _messageService);
            await windowVm.InitializeAsync(SelectedItem.LotId);

            var window = new LotDetailWindow(windowVm)
            {
                Owner = Application.Current?.MainWindow
            };

            window.ShowDialog();
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

                NormalizeSearchInputs();

                var result = await _apiClient.GetAsync<List<InspectionScheduleListItemDto>>(BuildListUrl());
                if (!result.Success || result.Data == null)
                {
                    Items.Clear();
                    TotalCount = 0;
                    TotalShipQty = 0;
                    SelectedItem = null;
                    EditModel.Clear();

                    _messageService.ShowError(result.Message ?? "검수 스케줄 목록 조회에 실패했습니다.");
                    return;
                }

                var selectedId = SelectedItem?.InspectionScheduleId;

                Items.Clear();
                foreach (var item in result.Data)
                {
                    Items.Add(item);
                }

                TotalCount = Items.Count;
                TotalShipQty = Items.Sum(x => x.ShipQty);

                if (selectedId.HasValue)
                {
                    SelectedItem = Items.FirstOrDefault(x => x.InspectionScheduleId == selectedId.Value);
                }
                else
                {
                    SelectedItem = null;
                    EditModel.Clear();
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        public Task ResetAsync()
        {
            SearchDate = DateTime.Today;
            Status = string.Empty;
            PartnerQuery = string.Empty;
            ProductQuery = string.Empty;
            SelectedItem = null;
            EditModel.Clear();

            return LoadAsync();
        }

        public Task SelectItemAsync(InspectionScheduleListItemDto? item)
        {
            if (item == null)
            {
                return Task.CompletedTask;
            }

            SelectedItem = item;
            return Task.CompletedTask;
        }

        public Task ClearSelectionAsync()
        {
            SelectedItem = null;
            EditModel.Clear();
            return Task.CompletedTask;
        }

        private Task OpenLabelPrintWindowAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("라벨을 인쇄할 스케줄 행을 선택해주세요.");
                return Task.CompletedTask;
            }

            var window = new InspectionLabelPrintWindow(
                SelectedItem.ProductName,
                SelectedItem.ProductSpec ?? string.Empty,
                SelectedItem.LotNo,
                IsManualLabelLotProduct(SelectedItem.ProductCode))
            {
                Owner = Application.Current?.MainWindow
            };

            window.ShowDialog();
            return Task.CompletedTask;
        }

        private static bool IsManualLabelLotProduct(string? productCode)
        {
            var normalized = productCode?.Trim() ?? string.Empty;
            return normalized.StartsWith("CU", StringComparison.OrdinalIgnoreCase) ||
                   normalized.StartsWith("AK", StringComparison.OrdinalIgnoreCase);
        }

        public async Task OpenInspectionResultAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("대상을 선택해주세요.");
                return;
            }

            if (SelectedItem.Status != "IN_PROGRESS")
            {
                _messageService.ShowWarning("검수완료는 진행중 상태에서만 가능합니다.");
                return;
            }

            if (!_canWriteInspection)
            {
                _messageService.ShowWarning("검수실적을 저장할 권한이 없습니다.");
                return;
            }

            var windowVm = new InspectionResultWindowViewModel(
                _apiClient,
                _messageService,
                _canWriteInspection);
            await windowVm.InitializeAsync(
                SelectedItem.InspectionScheduleId,
                SelectedItem.LotNo ?? string.Empty,
                SelectedItem.ProductName ?? string.Empty,
                SelectedItem.PartnerName ?? string.Empty,
                SelectedItem.InspectionDate,
                SelectedItem.LotQty,
                SelectedItem.DueDate,
                SelectedItem.OrderQty);

            var window = new InspectionResultWindow(windowVm)
            {
                Owner = Application.Current?.MainWindow
            };

            var dialogResult = window.ShowDialog();
            if (dialogResult == true)
            {
                await LoadAsync();
            }
        }


        public async Task OnInspectionDatePickedAsync(DateTime? previousDate, DateTime? selectedDate)
        {
            if (_isHandlingDateChange)
            {
                return;
            }

            if (SelectedItem == null)
            {
                return;
            }

            var originalDate = (previousDate ?? SelectedItem.InspectionDate).Date;

            if (!selectedDate.HasValue)
            {
                _isHandlingDateChange = true;
                SelectedItem.InspectionDate = originalDate;
                EditModel.InspectionDate = originalDate;
                _isHandlingDateChange = false;
                return;
            }

            var targetDate = selectedDate.Value.Date;

            if (targetDate == originalDate)
            {
                return;
            }
            if (targetDate < DateTime.Today.Date)
            {
                _messageService.ShowWarning("검수일정은 오늘 이전 날짜로 변경할 수 없습니다.");
                _isHandlingDateChange = true;
                SelectedItem.InspectionDate = originalDate;
                EditModel.InspectionDate = originalDate;
                _isHandlingDateChange = false;
                return;
            }
            if (!CanChangeDate())
            {
                _messageService.ShowWarning("일정변경은 대기 또는 입고완료 상태에서만 가능합니다.");

                _isHandlingDateChange = true;
                SelectedItem.InspectionDate = originalDate;
                EditModel.InspectionDate = originalDate;
                _isHandlingDateChange = false;
                return;
            }

            var confirm = _messageService.Confirm(
                $"LOT [{SelectedItem.LotNo}]의 검수일정을 [{targetDate:yyyy-MM-dd}]로 변경하시겠습니까?");

            if (!confirm)
            {
                _isHandlingDateChange = true;
                SelectedItem.InspectionDate = originalDate;
                EditModel.InspectionDate = originalDate;
                _isHandlingDateChange = false;
                return;
            }

            try
            {
                IsLoading = true;

                var request = new InspectionScheduleUpdateRequest
                {
                    InspectionDate = targetDate
                };

                var result = await _apiClient.PatchAsync<InspectionScheduleUpdateRequest, object>(
                    $"{ApiRoutes.InspectionSchedules}/{SelectedItem.InspectionScheduleId}",
                    request);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "검수 일정 변경에 실패했습니다.");

                    _isHandlingDateChange = true;
                    SelectedItem.InspectionDate = originalDate;
                    EditModel.InspectionDate = originalDate;
                    _isHandlingDateChange = false;
                    return;
                }

                _messageService.ShowInfo("검수 일정이 변경되었습니다.");

                await LoadAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        public async Task ReceiveAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("대상을 선택해주세요.");
                return;
            }

            if (!CanReceive())
            {
                _messageService.ShowWarning("입고완료는 대기 상태에서만 가능합니다.");
                return;
            }

            var confirm = _messageService.Confirm(
                $"LOT [{SelectedItem.LotNo}]를 입고완료 처리하시겠습니까?");
            if (!confirm)
            {
                return;
            }

            try
            {
                IsLoading = true;

                var result = await _apiClient.PostAsync<object, object>(
                    $"{ApiRoutes.InspectionSchedules}/{SelectedItem.InspectionScheduleId}/receive",
                    new { });

                if (!result.Success)
                {
                    var message = result.Message ?? "입고완료 처리에 실패했습니다.";

                    if (message.Contains("OUTSOURCE steps must be DONE before receiving", StringComparison.OrdinalIgnoreCase))
                    {
                        _messageService.ShowWarning("외주공정이 완료되지 않았습니다.");
                        return;
                    }

                    _messageService.ShowError(message);
                    return;
                }

                _messageService.ShowInfo("입고완료 처리되었습니다.");
                await LoadAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        public async Task StartAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("대상을 선택해주세요.");
                return;
            }

            if (!CanStart())
            {
                _messageService.ShowWarning("검수시작은 입고완료 상태에서만 가능합니다.");
                return;
            }

            var confirm = _messageService.Confirm(
                $"LOT [{SelectedItem.LotNo}]의 검수를 시작하시겠습니까?");

            if (!confirm)
            {
                return;
            }

            try
            {
                IsLoading = true;

                var result = await _apiClient.PostAsync<object, object>(
                    $"{ApiRoutes.InspectionSchedules}/{SelectedItem.InspectionScheduleId}/start",
                    new { });

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "검수시작 처리에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("검수가 시작되었습니다.");
                await LoadAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        public async Task CancelAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("대상을 선택해주세요.");
                return;
            }

            if (!CanCancel())
            {
                _messageService.ShowWarning("취소는 대기 또는 입고완료 상태에서만 가능합니다.");
                return;
            }

            var confirm = _messageService.Confirm(
                $"LOT [{SelectedItem.LotNo}]의 검수일정을 취소하시겠습니까?");

            if (!confirm)
            {
                return;
            }

            try
            {
                IsLoading = true;

                var result = await _apiClient.PostAsync<object, object>(
                    $"{ApiRoutes.InspectionSchedules}/{SelectedItem.InspectionScheduleId}/cancel",
                    new { });

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "검수 일정 취소에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("검수 일정이 취소되었습니다.");
                await LoadAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task OpenDrawingAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("대상을 선택해주세요.");
                return;
            }

            if (SelectedItem.DrawingId <= 0)
            {
                _messageService.ShowWarning("도면 정보가 없습니다.");
                return;
            }

            await _drawingViewer.OpenCurrentDrawingAsync(SelectedItem.DrawingId);
        }

        private async Task OpenPlateDataAsync(InspectionScheduleListItemDto? item)
        {
            if (item == null || !item.HasBundle)
            {
                return;
            }

            SelectedItem = item;

            try
            {
                var tempFolder = Path.Combine(
                    Path.GetTempPath(),
                    "Mes.Wpf",
                    "PlateData");

                Directory.CreateDirectory(tempFolder);

                var safeFileName = BuildSafePlateDataFileName(item.PlateDataFileName);
                var tempFilePath = Path.Combine(tempFolder, safeFileName);

                var download = await _apiClient.DownloadFileAsync(
                    $"{ApiRoutes.InspectionSchedules}/{item.InspectionScheduleId}/plate-data",
                    tempFilePath);

                if (!download.Success)
                {
                    _messageService.ShowError(
                        download.Message ?? "판데이터 파일을 다운로드할 수 없습니다.");
                    return;
                }

                Process.Start(new ProcessStartInfo
                {
                    FileName = tempFilePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                _messageService.ShowError($"판데이터 파일 열기 중 오류가 발생했습니다.\n{ex.Message}");
            }
        }

        private static string BuildSafePlateDataFileName(string? fileName)
        {
            var name = string.IsNullOrWhiteSpace(fileName)
                ? $"plate_data_{DateTime.Now:yyyyMMddHHmmss}"
                : fileName.Trim();

            foreach (var invalidChar in Path.GetInvalidFileNameChars())
            {
                name = name.Replace(invalidChar, '_');
            }

            name = name.Replace("/", "_").Replace("\\", "_").Trim();

            if (string.IsNullOrWhiteSpace(name) || name == "." || name == "..")
            {
                name = $"plate_data_{DateTime.Now:yyyyMMddHHmmss}";
            }

            if (string.IsNullOrWhiteSpace(Path.GetExtension(name)))
            {
                name += ".bin";
            }

            var extension = Path.GetExtension(name);
            var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(name);

            if (fileNameWithoutExtension.Length > 120)
            {
                fileNameWithoutExtension = fileNameWithoutExtension.Substring(0, 120);
            }

            return $"{fileNameWithoutExtension}{extension}";
        }

        public Task MoveUpAsync()
        {
            return ReorderBySwapAsync(true);
        }

        public Task MoveDownAsync()
        {
            return ReorderBySwapAsync(false);
        }

        private async Task ReorderBySwapAsync(bool moveUp)
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("대상을 선택해주세요.");
                return;
            }

            if (!(SelectedItem.Status == "WAITING" || SelectedItem.Status == "RECEIVED"))
            {
                _messageService.ShowWarning("순서변경은 대기 또는 입고완료 상태에서만 가능합니다.");
                return;
            }

            var sameDateItems = Items
                .Where(x =>
                    x.InspectionDate.Date == SelectedItem.InspectionDate.Date &&
                    (x.Status == "WAITING" || x.Status == "RECEIVED"))
                .OrderBy(x => x.DaySeq ?? int.MaxValue)
                .ThenBy(x => x.InspectionScheduleId)
                .ToList();

            var currentIndex = sameDateItems.FindIndex(x => x.InspectionScheduleId == SelectedItem.InspectionScheduleId);
            if (currentIndex < 0)
            {
                return;
            }

            var targetIndex = moveUp ? currentIndex - 1 : currentIndex + 1;
            if (targetIndex < 0 || targetIndex >= sameDateItems.Count)
            {
                return;
            }

            var current = sameDateItems[currentIndex];
            sameDateItems[currentIndex] = sameDateItems[targetIndex];
            sameDateItems[targetIndex] = current;

            try
            {
                IsLoading = true;

                var request = new InspectionScheduleReorderRequest
                {
                    InspectionDate = SelectedItem.InspectionDate.Date,
                    OrderedIds = sameDateItems.Select(x => x.InspectionScheduleId).ToList()
                };

                var result = await _apiClient.PutAsync<InspectionScheduleReorderRequest, object>(
                    $"{ApiRoutes.InspectionSchedules}/reorder",
                    request);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "검수 순서 변경에 실패했습니다.");
                    return;
                }

                await LoadAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string>
            {
                "limit=200",
                "offset=0"
            };

            if (SearchDate.HasValue)
            {
                queryParts.Add($"inspection_date_from={SearchDate.Value:yyyy-MM-dd}");
                queryParts.Add($"inspection_date_to={SearchDate.Value:yyyy-MM-dd}");
            }

            if (!string.IsNullOrWhiteSpace(Status))
            {
                queryParts.Add($"status={Uri.EscapeDataString(Status.Trim())}");
            }

            if (!string.IsNullOrWhiteSpace(PartnerQuery))
            {
                queryParts.Add($"partner_q={Uri.EscapeDataString(PartnerQuery.Trim())}");
            }

            if (!string.IsNullOrWhiteSpace(ProductQuery))
            {
                queryParts.Add($"product_q={Uri.EscapeDataString(ProductQuery.Trim())}");
            }

            return $"{ApiRoutes.InspectionSchedules}?{string.Join("&", queryParts)}";
        }



        private void NormalizeSearchInputs()
        {
            Status = Status?.Trim().ToUpperInvariant() ?? string.Empty;
            PartnerQuery = PartnerQuery?.Trim() ?? string.Empty;
            ProductQuery = ProductQuery?.Trim() ?? string.Empty;
            EditModel.Memo = EditModel.Memo?.Trim() ?? string.Empty;
        }

        private bool CanChangeDate()
        {
            return SelectedItem != null &&
                   _canWriteInspection &&
                   (SelectedItem.Status == "WAITING" || SelectedItem.Status == "RECEIVED");
        }

        private bool CanReceive()
        {
            return SelectedItem != null && _canWriteInspection && SelectedItem.Status == "WAITING";
        }

        private bool CanStart()
        {
            return SelectedItem != null && _canWriteInspection && SelectedItem.Status == "RECEIVED";
        }

        private bool CanCancel()
        {
            return SelectedItem != null &&
                   _canWriteInspection &&
                   (SelectedItem.Status == "WAITING" || SelectedItem.Status == "RECEIVED");
        }

        private bool CanMoveUp()
        {
            if (!_canWriteInspection ||
                SelectedItem == null ||
                !(SelectedItem.Status == "WAITING" || SelectedItem.Status == "RECEIVED"))
            {
                return false;
            }

            var sameDateItems = Items
                .Where(x =>
                    x.InspectionDate.Date == SelectedItem.InspectionDate.Date &&
                    (x.Status == "WAITING" || x.Status == "RECEIVED"))
                .OrderBy(x => x.DaySeq ?? int.MaxValue)
                .ThenBy(x => x.InspectionScheduleId)
                .ToList();

            var currentIndex = sameDateItems.FindIndex(x => x.InspectionScheduleId == SelectedItem.InspectionScheduleId);
            return currentIndex > 0;
        }

        private bool CanMoveDown()
        {
            if (!_canWriteInspection ||
                SelectedItem == null ||
                !(SelectedItem.Status == "WAITING" || SelectedItem.Status == "RECEIVED"))
            {
                return false;
            }

            var sameDateItems = Items
                .Where(x =>
                    x.InspectionDate.Date == SelectedItem.InspectionDate.Date &&
                    (x.Status == "WAITING" || x.Status == "RECEIVED"))
                .OrderBy(x => x.DaySeq ?? int.MaxValue)
                .ThenBy(x => x.InspectionScheduleId)
                .ToList();

            var currentIndex = sameDateItems.FindIndex(x => x.InspectionScheduleId == SelectedItem.InspectionScheduleId);
            return currentIndex >= 0 && currentIndex < sameDateItems.Count - 1;
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

            if (ClearSelectionCommand is AsyncRelayCommand clearSelectionCommand)
            {
                clearSelectionCommand.RaiseCanExecuteChanged();
            }

            if (PrintLabelCommand is AsyncRelayCommand printLabelCommand)
            {
                printLabelCommand.RaiseCanExecuteChanged();
            }

            if (SelectItemCommand is AsyncRelayCommand<InspectionScheduleListItemDto> selectItemCommand)
            {
                selectItemCommand.RaiseCanExecuteChanged();
            }

            if (ReceiveCommand is AsyncRelayCommand receiveCommand)
            {
                receiveCommand.RaiseCanExecuteChanged();
            }

            if (StartCommand is AsyncRelayCommand startCommand)
            {
                startCommand.RaiseCanExecuteChanged();
            }

            if (CancelCommand is AsyncRelayCommand cancelCommand)
            {
                cancelCommand.RaiseCanExecuteChanged();
            }

            if (MoveUpCommand is AsyncRelayCommand moveUpCommand)
            {
                moveUpCommand.RaiseCanExecuteChanged();
            }

            if (MoveDownCommand is AsyncRelayCommand moveDownCommand)
            {
                moveDownCommand.RaiseCanExecuteChanged();
            }

            if (OpenLotDetailCommand is AsyncRelayCommand openLotDetailCommand)
            {
                openLotDetailCommand.RaiseCanExecuteChanged();
            }

            if (OpenDrawingCommand is AsyncRelayCommand openDrawingCommand)
            {
                openDrawingCommand.RaiseCanExecuteChanged();
            }

            if (OpenPlateDataCommand is AsyncRelayCommand<InspectionScheduleListItemDto> openPlateDataCommand)
            {
                openPlateDataCommand.RaiseCanExecuteChanged();
            }
        }
    }
}
