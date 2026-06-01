using ClosedXML.Excel;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Inventories.Dtos;
using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Inventories.ViewModels
{
    public class InitialInventoryBulkUploadWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _bulkFilePath = string.Empty;
        private string _bulkSummaryText = "대기 중";
        private string _loadingMessage = "처리 중입니다...";
        private bool _isLoading;

        public InitialInventoryBulkUploadWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Rows = new ObservableCollection<InitialInventoryBulkUploadRowModel>();

            DownloadTemplateCommand = new AsyncRelayCommand(DownloadTemplateAsync);
            SelectFileCommand = new AsyncRelayCommand(SelectFileAsync);
            UploadCommand = new AsyncRelayCommand(UploadAsync);
            ClearCommand = new RelayCommand(ClearRows);
            CloseCommand = new RelayCommand(() => RequestClose?.Invoke());
        }

        public event Action? RequestClose;
        public event Action? UploadCompleted;

        public ObservableCollection<InitialInventoryBulkUploadRowModel> Rows { get; }

        public AsyncRelayCommand DownloadTemplateCommand { get; }
        public AsyncRelayCommand SelectFileCommand { get; }
        public AsyncRelayCommand UploadCommand { get; }
        public RelayCommand ClearCommand { get; }
        public RelayCommand CloseCommand { get; }

        public string BulkFilePath
        {
            get => _bulkFilePath;
            set => SetProperty(ref _bulkFilePath, value);
        }

        public string BulkSummaryText
        {
            get => _bulkSummaryText;
            set => SetProperty(ref _bulkSummaryText, value);
        }

        public string LoadingMessage
        {
            get => _loadingMessage;
            set => SetProperty(ref _loadingMessage, value);
        }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        private async Task DownloadTemplateAsync()
        {
            var dialog = new SaveFileDialog
            {
                Title = "기초재고 업로드 템플릿 저장",
                Filter = "Excel Files (*.xlsx)|*.xlsx",
                FileName = "initial_inventory_upload_template.xlsx",
                DefaultExt = ".xlsx"
            };

            if (dialog.ShowDialog() != true)
            {
                return;
            }

            IsLoading = true;
            LoadingMessage = "템플릿 생성 중...";

            await Task.Yield();

            try
            {
                var requestedPath = dialog.FileName;
                var targetPath = GetAvailableTemplatePath(requestedPath);

                await Task.Run(() =>
                {
                    using var workbook = new XLWorkbook();
                    var worksheet = workbook.Worksheets.Add("InitialInventory");

                    worksheet.Cell(1, 1).Value = "product_code";
                    worksheet.Cell(1, 2).Value = "lot_no";
                    worksheet.Cell(1, 3).Value = "initial_qty";
                    worksheet.Cell(1, 4).Value = "memo";

                    worksheet.Cell(2, 1).Value = "P-001";
                    worksheet.Cell(2, 2).Value = "LOT-001";
                    worksheet.Cell(2, 3).Value = 1000;
                    worksheet.Cell(2, 4).Value = "오픈 전 실사 재고";

                    worksheet.Columns().AdjustToContents();

                    workbook.SaveAs(targetPath);
                });

                if (!string.Equals(requestedPath, targetPath, StringComparison.OrdinalIgnoreCase))
                {
                    _messageService.ShowInfo($"선택한 파일이 이미 있어서 새 파일명으로 저장했습니다.\n{targetPath}");
                }
                else
                {
                    _messageService.ShowInfo("기초재고 업로드 템플릿이 저장되었습니다.");
                }
            }
            catch (Exception ex)
            {
                _messageService.ShowError($"템플릿 생성 중 오류가 발생했습니다.\n{ex.Message}");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private static string GetAvailableTemplatePath(string requestedPath)
        {
            if (!File.Exists(requestedPath))
            {
                return requestedPath;
            }

            var directory = Path.GetDirectoryName(requestedPath) ?? string.Empty;
            var fileName = Path.GetFileNameWithoutExtension(requestedPath);
            var extension = Path.GetExtension(requestedPath);
            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss", CultureInfo.InvariantCulture);

            var candidate = Path.Combine(directory, $"{fileName}_{timestamp}{extension}");
            var sequence = 1;

            while (File.Exists(candidate))
            {
                candidate = Path.Combine(directory, $"{fileName}_{timestamp}_{sequence}{extension}");
                sequence++;
            }

            return candidate;
        }

        private async Task SelectFileAsync()
        {
            var dialog = new OpenFileDialog
            {
                Title = "기초재고 업로드 파일 선택",
                Filter = "Excel Files (*.xlsx)|*.xlsx",
                Multiselect = false
            };

            if (dialog.ShowDialog() != true)
            {
                return;
            }

            IsLoading = true;
            LoadingMessage = "엑셀 파일 읽는 중...";

            await Task.Yield();

            try
            {
                var selectedPath = dialog.FileName;
                var rows = await Task.Run(() => ParseRowsFromExcel(selectedPath).ToList());

                Rows.Clear();

                foreach (var row in rows.OrderBy(x => x.RowNumber))
                {
                    Rows.Add(row);
                }

                BulkFilePath = selectedPath;

                NormalizeRows();
                ValidateRows();
            }
            catch (Exception ex)
            {
                Rows.Clear();
                BulkFilePath = string.Empty;
                BulkSummaryText = "대기 중";

                _messageService.ShowError($"엑셀 파일을 읽는 중 오류가 발생했습니다.\n{ex.Message}");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private async Task UploadAsync()
        {
            if (IsLoading)
            {
                return;
            }

            NormalizeRows();
            ValidateRows();

            var uploadRows = Rows.Where(x => x.IsValid).ToList();

            if (uploadRows.Count == 0)
            {
                _messageService.ShowWarning("등록할 유효 데이터가 없습니다.");
                return;
            }

            var confirmed = _messageService.Confirm(
                $"유효 데이터 {uploadRows.Count}건을 기초재고로 등록하시겠습니까?\n이미 재고 이력이 있는 품목은 백엔드에서 오류 처리됩니다.",
                "기초재고 등록 확인");

            if (!confirmed)
            {
                return;
            }

            IsLoading = true;
            LoadingMessage = "기초재고 등록 중...";

            await Task.Yield();

            try
            {
                var request = new InitialInventoryBulkRequest
                {
                    Items = uploadRows.Select(x => new InitialInventoryBulkItemRequest
                    {
                        RowNumber = x.RowNumber,
                        ProductCode = x.ProductCode,
                        LotNo = x.LotNo,
                        InitialQty = x.InitialQty,
                        Memo = x.Memo
                    }).ToList()
                };

                var result = await _apiClient.PostAsync<InitialInventoryBulkRequest, InitialInventoryBulkResultDto>(
                    ApiRoutes.InitialInventoryBulk,
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "기초재고 등록 중 오류가 발생했습니다.");
                    return;
                }

                ApplyUploadResult(result.Data);

                UploadCompleted?.Invoke();
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private void ClearRows()
        {
            Rows.Clear();
            BulkFilePath = string.Empty;
            BulkSummaryText = "대기 중";
        }

        private IEnumerable<InitialInventoryBulkUploadRowModel> ParseRowsFromExcel(string filePath)
        {
            using var workbook = OpenWorkbookForUpload(filePath);
            var worksheet = workbook.Worksheets.First();

            var lastRow = worksheet.LastRowUsed()?.RowNumber() ?? 1;

            for (var rowNumber = 2; rowNumber <= lastRow; rowNumber++)
            {
                var productCode = worksheet.Cell(rowNumber, 1).GetString();
                var lotNo = worksheet.Cell(rowNumber, 2).GetString();
                var qtyText = worksheet.Cell(rowNumber, 3).GetFormattedString();
                var memo = worksheet.Cell(rowNumber, 4).GetString();

                if (string.IsNullOrWhiteSpace(productCode)
                    && string.IsNullOrWhiteSpace(lotNo)
                    && string.IsNullOrWhiteSpace(qtyText)
                    && string.IsNullOrWhiteSpace(memo))
                {
                    continue;
                }

                var initialQty = ParseQty(qtyText);

                yield return new InitialInventoryBulkUploadRowModel
                {
                    RowNumber = rowNumber,
                    ProductCode = productCode,
                    LotNo = lotNo,
                    InitialQty = initialQty,
                    Memo = string.IsNullOrWhiteSpace(memo) ? null : memo
                };
            }
        }

        private static XLWorkbook OpenWorkbookForUpload(string filePath)
        {
            using var fileStream = new FileStream(
                filePath,
                FileMode.Open,
                FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete);

            var memoryStream = new MemoryStream();
            fileStream.CopyTo(memoryStream);
            memoryStream.Position = 0;

            return new XLWorkbook(memoryStream);
        }

        private static int ParseQty(string text)
        {
            var normalized = (text ?? string.Empty).Trim().Replace(",", string.Empty);

            if (string.IsNullOrWhiteSpace(normalized))
            {
                return 0;
            }

            if (int.TryParse(normalized, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value))
            {
                return value;
            }

            return -1;
        }

        private void NormalizeRows()
        {
            foreach (var row in Rows)
            {
                row.ProductCode = (row.ProductCode ?? string.Empty).Trim().ToUpperInvariant();
                row.LotNo = (row.LotNo ?? string.Empty).Trim().ToUpperInvariant();
                row.Memo = string.IsNullOrWhiteSpace(row.Memo) ? null : row.Memo.Trim();
                row.ClearValidation();
            }
        }

        private void ValidateRows()
        {
            var seenLots = new Dictionary<string, int>();

            foreach (var row in Rows.OrderBy(x => x.RowNumber))
            {
                if (string.IsNullOrWhiteSpace(row.ProductCode))
                {
                    row.MarkError("품목코드는 필수입니다.");
                    continue;
                }

                if (string.IsNullOrWhiteSpace(row.LotNo))
                {
                    row.MarkError("LOT 번호는 필수입니다.");
                    continue;
                }

                if (row.InitialQty < 0)
                {
                    row.MarkError("기초재고 수량은 0 이상의 숫자여야 합니다.");
                    continue;
                }

                var duplicateKey = $"{row.ProductCode}|{row.LotNo}";
                if (seenLots.TryGetValue(duplicateKey, out var firstRowNumber))
                {
                    row.MarkError($"엑셀 내 중복 품목/LOT입니다. 첫 행: {firstRowNumber}");
                    continue;
                }

                seenLots[duplicateKey] = row.RowNumber;

                if (row.InitialQty == 0)
                {
                    row.MarkSkipped("기초재고 0은 등록 제외됩니다.");
                    continue;
                }

                row.ClearValidation();
            }

            var validCount = Rows.Count(x => x.IsValid);
            var skippedCount = Rows.Count(x => x.Status == "제외");
            var errorCount = Rows.Count(x => x.Status == "오류");

            BulkSummaryText = $"검증 완료 - 전체: {Rows.Count}건 / 유효: {validCount}건 / 제외: {skippedCount}건 / 오류: {errorCount}건";
        }

        private void ApplyUploadResult(InitialInventoryBulkResultDto result)
        {
            var errorRowNumbers = result.Errors
                .Select(x => x.RowNumber)
                .ToHashSet();

            foreach (var error in result.Errors)
            {
                var target = Rows.FirstOrDefault(x => x.RowNumber == error.RowNumber);

                if (target != null)
                {
                    target.MarkError(error.Message);
                }
            }

            if (result.FailureCount == 0)
            {
                Rows.Clear();
                BulkFilePath = string.Empty;

                BulkSummaryText =
                    $"등록 완료 - 성공: {result.SuccessCount}건 / 제외: {result.SkippedCount}건 / 실패: 0건 / 전체: {result.TotalCount}건";

                _messageService.ShowInfo("기초재고 등록이 완료되었습니다.");
                return;
            }

            var rowsToRemove = Rows
                .Where(x => !errorRowNumbers.Contains(x.RowNumber))
                .ToList();

            foreach (var row in rowsToRemove)
            {
                Rows.Remove(row);
            }

            BulkFilePath = string.Empty;

            BulkSummaryText =
                $"일부 등록 완료 - 성공: {result.SuccessCount}건 / 제외: {result.SkippedCount}건 / 실패: {result.FailureCount}건 / 전체: {result.TotalCount}건";

            _messageService.ShowWarning("일부 행에 오류가 있습니다. 오류 내용을 확인한 뒤 엑셀을 수정해서 다시 선택하세요.");
        }
    }
}
