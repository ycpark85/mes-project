using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Win32;
using System.IO;

using static Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos.OutsourcePurchaseOrderEditModel;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels
{
    public class OutsourcePurchaseOrderPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private OutsourcePurchaseOrderBundleRowModel? _selectedBundle;
        private OutsourcePurchaseOrderResponse? _savedPurchaseOrder;

        public OutsourcePurchaseOrderPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            CutGroups = new ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel>();
            PrintGroups = new ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel>();
            Bundles = new ObservableCollection<OutsourcePurchaseOrderBundleRowModel>();

            CutEditModel = new OutsourceCutPurchaseOrderEditModel();
            PrintEditModel = new OutsourcePrintPurchaseOrderEditModel();

            RefreshCommand = new AsyncRelayCommand(SearchAsync);
            ResetCommand = new RelayCommand(Reset);
            SaveCommand = new AsyncRelayCommand(SaveAsync);
            PrintCommand = new RelayCommand(Print);
        }

        public ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> CutGroups { get; }

        public ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> PrintGroups { get; }

        public ObservableCollection<OutsourcePurchaseOrderBundleRowModel> Bundles { get; }

        public OutsourceCutPurchaseOrderEditModel CutEditModel { get; }
        public OutsourcePrintPurchaseOrderEditModel PrintEditModel { get; }

        public OutsourcePurchaseOrderResponse? SavedPurchaseOrder
        {
            get => _savedPurchaseOrder;
            set => SetProperty(ref _savedPurchaseOrder, value);
        }

        public AsyncRelayCommand RefreshCommand { get; }

        public RelayCommand ResetCommand { get; }

        public AsyncRelayCommand SaveCommand { get; }

        public RelayCommand PrintCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public OutsourcePurchaseOrderBundleRowModel? SelectedBundle
        {
            get => _selectedBundle;
            set
            {
                if (!SetProperty(ref _selectedBundle, value))
                {
                    return;
                }

                if (value != null && string.Equals(value.BundleType, "CUT", StringComparison.OrdinalIgnoreCase))
                {
                    CutEditModel.LoadFromBundle(value);
                    PrintEditModel.Clear();
                }
                else if (value != null && string.Equals(value.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase))
                {
                    CutEditModel.Clear();
                    PrintEditModel.LoadFromBundle(value);
                }
                else
                {
                    CutEditModel.Clear();
                    PrintEditModel.Clear();
                }

                OnPropertyChanged(nameof(IsCutBundleSelected));
                OnPropertyChanged(nameof(IsPrintBundleSelected));
            }
        }

        public bool IsCutBundleSelected => string.Equals(SelectedBundle?.BundleType, "CUT", StringComparison.OrdinalIgnoreCase);
        public bool IsPrintBundleSelected => string.Equals(SelectedBundle?.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase);

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            IsLoading = true;
            try
            {
                await LoadGroupsAsync("CUT", CutGroups);
                await LoadGroupsAsync("PRINT", PrintGroups);
                BuildBundles();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task LoadGroupsAsync(
            string processType,
            ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> targetCollection)
        {
            var route =
                $"{ApiRoutes.OutsourcePurchaseOrderTargets}?process_type={Uri.EscapeDataString(processType)}";

            var result = await _apiClient.GetAsync<OutsourcePurchaseOrderTargetListDto>(route);

            if (result == null || !result.Success || result.Data == null)
            {
                targetCollection.Clear();
                _messageService.ShowError(
                    result?.Message ?? $"{processType} 발주 대상 조회 중 오류가 발생했습니다.");
                return;
            }

            var grouped = result.Data.Items
                .GroupBy(x => new
                {
                    x.OutsourceWorkInstructionId,
                    x.InstructionNo,
                    x.ProcessType
                })
                .Select(g =>
                {
                    var first = g.First();

                    var fileMap = new Dictionary<long, OutsourceWorkInstructionFileDto>();
                    foreach (var row in g)
                    {
                        foreach (var file in row.Files)
                        {
                            if (!fileMap.ContainsKey(file.OutsourceWorkInstructionFileId))
                            {
                                fileMap[file.OutsourceWorkInstructionFileId] = file;
                            }
                        }
                    }

                    return new OutsourcePurchaseOrderTargetGroupRowModel
                    {
                        OutsourceWorkInstructionId = first.OutsourceWorkInstructionId,
                        InstructionNo = first.InstructionNo,
                        InstructionDate = first.InstructionDate,
                        ProcessType = first.ProcessType,
                        IsBundle = first.IsBundle,
                        OutsourcePartnerId = first.OutsourcePartnerId,
                        OutsourcePartnerName = first.OutsourcePartnerName ?? string.Empty,
                        InboundPartnerName = first.InboundPartnerName ?? string.Empty,
                        Items = g.OrderBy(x => x.LotNo).ToList(),
                        Files = fileMap.Values.ToList()
                    };
                })
                .OrderByDescending(x => x.InstructionDate)
                .ThenByDescending(x => x.InstructionNo)
                .ToList();

            targetCollection.Clear();
            foreach (var item in grouped)
            {
                targetCollection.Add(item);
            }
        }

        private void BuildBundles()
        {
            Bundles.Clear();

            if (CutGroups.Count > 0)
            {
                Bundles.Add(new OutsourcePurchaseOrderBundleRowModel
                {
                    BundleType = "CUT",
                    Title = "재단 발주묶음",
                    Groups = CutGroups.ToList(),
                    Items = CutGroups
                        .SelectMany(x => x.Items)
                        .OrderBy(x => x.LotNo)
                        .ToList(),
                    Files = CutGroups
                        .SelectMany(x => x.Files)
                        .GroupBy(x => x.OutsourceWorkInstructionFileId)
                        .Select(x => x.First())
                        .ToList()
                });
            }

            if (PrintGroups.Count > 0)
            {
                Bundles.Add(new OutsourcePurchaseOrderBundleRowModel
                {
                    BundleType = "PRINT",
                    Title = "인쇄 발주묶음",
                    Groups = PrintGroups.ToList(),
                    Items = PrintGroups
                        .SelectMany(x => x.Items)
                        .OrderBy(x => x.LotNo)
                        .ToList(),
                    Files = PrintGroups
                        .SelectMany(x => x.Files)
                        .GroupBy(x => x.OutsourceWorkInstructionFileId)
                        .Select(x => x.First())
                        .ToList()
                });
            }

            SelectedBundle = Bundles.FirstOrDefault();
            OnPropertyChanged(nameof(Bundles));
        }

        private void Reset()
        {
            SelectedBundle = null;
            SavedPurchaseOrder = null;
            CutEditModel.Clear();
            PrintEditModel.Clear();
            _ = SearchAsync();
        }

        private async Task SaveAsync()
        {
            if (IsLoading)
            {
                return;
            }

            if (SelectedBundle == null)
            {
                _messageService.ShowWarning("발주 대상을 선택하세요.");
                return;
            }

            if (string.Equals(SelectedBundle.BundleType, "CUT", StringComparison.OrdinalIgnoreCase))
            {
                NormalizeCutEditModel();
            }
            else if (string.Equals(SelectedBundle.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase))
            {
                NormalizePrintEditModel();
            }

            var validationMessage = ValidateForSave();
            if (!string.IsNullOrWhiteSpace(validationMessage))
            {
                _messageService.ShowWarning(validationMessage);
                return;
            }

            var request = BuildCreateRequest();
            var savedBundle = SelectedBundle;

            IsLoading = true;
            try
            {
                var result = await _apiClient.PostAsync<OutsourcePurchaseOrderCreateRequest, OutsourcePurchaseOrderResponse>(
                    ApiRoutes.OutsourcePurchaseOrders,
                    request);

                if (result == null || !result.Success || result.Data == null)
                {
                    _messageService.ShowError(result?.Message ?? "외주발주서 저장에 실패했습니다.");
                    return;
                }

                SavedPurchaseOrder = result.Data;

                RemoveSavedBundle(savedBundle);
                await SearchAsync();

                _messageService.ShowInfo($"저장되었습니다. 발주번호: {result.Data.PurchaseOrderNo}");

                
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void NormalizeCutEditModel()
        {
            CutEditModel.Title = CutEditModel.Title?.Trim() ?? string.Empty;
            CutEditModel.CompanyName = CutEditModel.CompanyName?.Trim() ?? string.Empty;
            CutEditModel.RequestPartnerName = CutEditModel.RequestPartnerName?.Trim() ?? string.Empty;
            CutEditModel.RequesterName = CutEditModel.RequesterName?.Trim() ?? string.Empty;
            CutEditModel.RawMaterialInboundText = CutEditModel.RawMaterialInboundText?.Trim() ?? string.Empty;
            CutEditModel.Remark = CutEditModel.Remark?.Trim() ?? string.Empty;
        }

        private string? ValidateForSave()
        {
            if (SelectedBundle == null)
            {
                return "저장할 발주 대상이 없습니다.";
            }

            if (!string.Equals(SelectedBundle.BundleType, "CUT", StringComparison.OrdinalIgnoreCase) &&
                !string.Equals(SelectedBundle.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase))
            {
                return "저장 가능한 발주 대상이 아닙니다.";
            }

            if (SelectedBundle.Groups == null || SelectedBundle.Groups.Count == 0)
            {
                return "저장할 그룹 정보가 없습니다.";
            }

            if (SelectedBundle.Items == null || SelectedBundle.Items.Count == 0)
            {
                return "저장할 LOT 항목이 없습니다.";
            }

            if (SelectedBundle.TotalQty <= 0)
            {
                return "수량을 확인하세요.";
            }

            var outsourcePartnerId = SelectedBundle.Groups
                .Select(x => x.OutsourcePartnerId)
                .FirstOrDefault(x => x > 0);

            if (outsourcePartnerId <= 0)
            {
                return "외주처 정보가 없습니다.";
            }

            if (string.Equals(SelectedBundle.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase) &&
                PrintEditModel.Items.Count == 0)
            {
                return "인쇄 발주서 행 정보가 없습니다.";
            }

            return null;
        }

        private OutsourcePurchaseOrderCreateRequest BuildCreateRequest()
        {
            var outsourcePartnerId = SelectedBundle!.Groups
                .Select(x => x.OutsourcePartnerId)
                .FirstOrDefault(x => x > 0);

            var isPrint = string.Equals(SelectedBundle.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase);

            return new OutsourcePurchaseOrderCreateRequest
            {
                PurchaseOrderDate = isPrint
                    ? (PrintEditModel.PurchaseOrderDate ?? DateTime.Today).ToString("yyyy-MM-dd")
                    : CutEditModel.RequestDate.ToString("yyyy-MM-dd"),
                DueDate = null,
                ProcessType = ResolveProcessType(),
                OutsourcePartnerId = outsourcePartnerId,
                InboundPartnerId = null,
                WorkDescription = ResolveWorkDescription(),
                Remark = isPrint ? PrintEditModel.FooterRemark : CutEditModel.Remark,
                Qty = SelectedBundle.TotalQty,
                UnitPrice = null,
                SupplyAmount = null,
                VatAmount = null,
                TotalAmount = null,
                Items = BuildCreateItems(),
                FormSnapshot = isPrint
                    ? BuildPrintFormSnapshot()
                    : BuildCutFormSnapshot()
            };
        }

        private OutsourcePurchaseOrderCutSnapshotRequest BuildCutFormSnapshot()
        {
            var snapshot = new OutsourcePurchaseOrderCutSnapshotRequest
            {
                RequestCompanyName = CutEditModel.RequestPartnerName?.Trim(),
                RequesterName = CutEditModel.RequesterName?.Trim(),
                PurchaseOrderDate = CutEditModel.RequestDate.ToString("yyyy-MM-dd"),
                RawMaterialInboundText = CutEditModel.RawMaterialInboundText?.Trim(),
                Stock500WidthText = CutEditModel.Stock500Width?.ToString("0.##"),
                Stock600WidthText = CutEditModel.Stock600Width?.ToString("0.##"),
                Stock600Tpt0268Text = CutEditModel.Stock600Tpt0268?.ToString("0.##"),
                Remark = CutEditModel.Remark?.Trim()
            };

            foreach (var item in CutEditModel.Items)
            {
                snapshot.Rows.Add(new OutsourcePurchaseOrderCutSnapshotRowRequest
                {
                    No = item.No,
                    RawMaterialText = item.RawMaterialText?.Trim(),
                    LengthMText = (item.SavedLengthM ?? item.LengthM)?.ToString("0.##"),
                    InboundPlaceText = item.InboundPlaceDisplay?.Trim(),
                    CutSpecText = item.CutSpec?.Trim(),
                    SheetQtyText = (item.SavedSheetQty ?? item.SheetQty)?.ToString()
                });
            }

            return snapshot;
        }

        private void NormalizePrintEditModel()
        {
            PrintEditModel.VendorName = PrintEditModel.VendorName?.Trim() ?? string.Empty;
            PrintEditModel.RequestCompanyName = PrintEditModel.RequestCompanyName?.Trim() ?? string.Empty;
            PrintEditModel.RequesterName = PrintEditModel.RequesterName?.Trim() ?? string.Empty;
            PrintEditModel.FooterRemark = PrintEditModel.FooterRemark?.Trim();

            foreach (var item in PrintEditModel.Items)
            {
                item.CustomerName = item.CustomerName?.Trim();
                item.ProductName = item.ProductName?.Trim();
                item.MaterialSpec = item.MaterialSpec?.Trim();
                item.Sample = item.Sample?.Trim();
                item.PlateCount = item.PlateCount?.Trim();
                item.ColorName = item.ColorName?.Trim();
                item.MaterialType = item.MaterialType?.Trim();
                item.Remark = item.Remark?.Trim();
            }
        }

        private OutsourcePurchaseOrderPrintSnapshotRequest BuildPrintFormSnapshot()
        {
            var snapshot = new OutsourcePurchaseOrderPrintSnapshotRequest
            {
                VendorName = PrintEditModel.VendorName?.Trim(),
                RequestCompanyName = PrintEditModel.RequestCompanyName?.Trim(),
                RequesterName = PrintEditModel.RequesterName?.Trim(),
                PurchaseOrderDate = (PrintEditModel.PurchaseOrderDate ?? DateTime.Today).ToString("yyyy-MM-dd"),
                FooterRemark = PrintEditModel.FooterRemark?.Trim()
            };

            foreach (var item in PrintEditModel.Items)
            {
                snapshot.Rows.Add(new OutsourcePurchaseOrderPrintSnapshotRowRequest
                {
                    No = item.No,
                    CustomerName = item.CustomerName?.Trim(),
                    ProductName = item.ProductName?.Trim(),
                    MaterialSpec = item.MaterialSpec?.Trim(),
                    PrintSheetQty = item.PrintSheetQty.ToString(),
                    Sample = item.Sample?.Trim(),
                    PlateCount = item.PlateCount?.Trim(),
                    ColorName = item.ColorName?.Trim(),
                    MaterialType = item.MaterialType?.Trim(),
                    Remark = item.Remark?.Trim()
                });
            }

            return snapshot;
        }



        private List<OutsourcePurchaseOrderCreateItemRequest> BuildCreateItems()
        {
            var items = new List<OutsourcePurchaseOrderCreateItemRequest>();

            if (SelectedBundle?.Items == null)
            {
                return items;
            }

            var seq = 1;
            foreach (var item in SelectedBundle.Items.OrderBy(x => x.LotNo))
            {
                items.Add(new OutsourcePurchaseOrderCreateItemRequest
                {
                    LotId = item.LotId,
                    OutsourceWorkInstructionId = item.OutsourceWorkInstructionId,
                    ItemSeq = seq++,
                    Qty = item.LotQty
                });
            }

            return items;
        }

        private string ResolveProcessType()
        {
            if (string.Equals(SelectedBundle?.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase))
            {
                return "PRINT";
            }

            return "CUT";
        }

        private string ResolveWorkDescription()
        {
            if (string.Equals(SelectedBundle?.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase))
            {
                return "인쇄 외주 작업";
            }

            return "재단 외주 작업";
        }

        private void Print()
        {
            
            _messageService.ShowInfo("출력 기능은 엑셀다운로드 방식으로 변경되었습니다.");
        }

        private void RemoveSavedBundle(OutsourcePurchaseOrderBundleRowModel? bundle)
        {
            if (bundle == null)
            {
                return;
            }

            var targetBundle = Bundles.FirstOrDefault(x => ReferenceEquals(x, bundle));
            if (targetBundle != null)
            {
                Bundles.Remove(targetBundle);
            }

            if (string.Equals(bundle.BundleType, "CUT", StringComparison.OrdinalIgnoreCase))
            {
                CutGroups.Clear();
            }
            else if (string.Equals(bundle.BundleType, "PRINT", StringComparison.OrdinalIgnoreCase))
            {
                PrintGroups.Clear();
            }

            SelectedBundle = Bundles.FirstOrDefault();
            OnPropertyChanged(nameof(Bundles));
            OnPropertyChanged(nameof(IsCutBundleSelected));
            OnPropertyChanged(nameof(IsPrintBundleSelected));
        }

        private async Task DownloadExcelAsync(long outsourcePurchaseOrderId, string purchaseOrderNo)
        {
            var route = $"{ApiRoutes.OutsourcePurchaseOrderExcel}/{outsourcePurchaseOrderId}/excel";
            var fileBytes = await _apiClient.GetBytesAsync(route);

            if (fileBytes == null || fileBytes.Length == 0)
            {
                _messageService.ShowWarning("엑셀 다운로드에 실패했습니다.");
                return;
            }

            var dialog = new SaveFileDialog
            {
                FileName = $"{purchaseOrderNo}.xlsx",
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
        }
    }
}