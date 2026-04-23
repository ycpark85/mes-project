using Mes.Wpf.Core.Common;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json.Serialization;
using static Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos.OutsourcePurchaseOrderEditModel;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos
{
    public class OutsourceWorkInstructionFileDto
    {
        [JsonPropertyName("outsource_work_instruction_file_id")]
        public long OutsourceWorkInstructionFileId { get; set; }

        [JsonPropertyName("file_name")]
        public string FileName { get; set; } = string.Empty;

        [JsonPropertyName("file_path")]
        public string FilePath { get; set; } = string.Empty;

        [JsonPropertyName("content_type")]
        public string? ContentType { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }

    public class OutsourceWorkInstructionCandidateLotDto
    {
        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("order_no")]
        public string OrderNo { get; set; } = string.Empty;

        [JsonPropertyName("line_no")]
        public int LineNo { get; set; }

        [JsonPropertyName("product_id")]
        public long ProductId { get; set; }

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("partner_id")]
        public long PartnerId { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("available_process_types")]
        public List<string> AvailableProcessTypes { get; set; } = new();

        [JsonPropertyName("panel_width_mm")]
        public int? PanelWidthMm { get; set; }

        [JsonPropertyName("panel_length_mm")]
        public int? PanelLengthMm { get; set; }

        [JsonPropertyName("product_spec")]
        public string? ProductSpec { get; set; }

        [JsonPropertyName("cut_qty_per_panel")]
        public int? CutQtyPerPanel { get; set; }
    }

    public class OutsourceWorkInstructionCandidateLotListDto
    {
        [JsonPropertyName("items")]
        public List<OutsourceWorkInstructionCandidateLotDto> Items { get; set; } = new();
    }

    public class OutsourceWorkInstructionCandidateLotRowModel : ViewModelBase
    {
        private bool _isSelected;
        private int? _manualCutsPerSheet;

        public long LotId { get; set; }
        public string LotNo { get; set; } = string.Empty;
        public long OrderLineId { get; set; }
        public string OrderNo { get; set; } = string.Empty;
        public int LineNo { get; set; }
        public long ProductId { get; set; }
        public string ProductCode { get; set; } = string.Empty;
        public string ProductName { get; set; } = string.Empty;
        public long PartnerId { get; set; }
        public string? PartnerName { get; set; }
        public int LotQty { get; set; }
        public List<string> AvailableProcessTypes { get; set; } = new();

        public int? PanelWidthMm { get; set; }
        public int? PanelLengthMm { get; set; }
        public string? ProductSpec { get; set; }
        public int? CutQtyPerPanel { get; set; }

        public int? ManualCutsPerSheet
        {
            get => _manualCutsPerSheet;
            set => SetProperty(ref _manualCutsPerSheet, value);
        }

        public string PlateSizeText =>
            PanelWidthMm.HasValue && PanelLengthMm.HasValue
                ? $"{PanelWidthMm.Value} x {PanelLengthMm.Value}"
                : string.Empty;

        public string SpecText => ProductSpec ?? string.Empty;

        public string CutCountText => CutQtyPerPanel?.ToString() ?? string.Empty;

        public bool IsSelected
        {
            get => _isSelected;
            set => SetProperty(ref _isSelected, value);
        }

        public string ProcessText => string.Join(" / ", AvailableProcessTypes);

        public static OutsourceWorkInstructionCandidateLotRowModel FromDto(OutsourceWorkInstructionCandidateLotDto dto)
        {
            return new OutsourceWorkInstructionCandidateLotRowModel
            {
                LotId = dto.LotId,
                LotNo = dto.LotNo,
                OrderLineId = dto.OrderLineId,
                OrderNo = dto.OrderNo,
                LineNo = dto.LineNo,
                ProductId = dto.ProductId,
                ProductCode = dto.ProductCode,
                ProductName = dto.ProductName,
                PartnerId = dto.PartnerId,
                PartnerName = dto.PartnerName,
                LotQty = dto.LotQty,
                AvailableProcessTypes = dto.AvailableProcessTypes ?? new List<string>(),
                PanelWidthMm = dto.PanelWidthMm,
                PanelLengthMm = dto.PanelLengthMm,
                ProductSpec = dto.ProductSpec,
                CutQtyPerPanel = dto.CutQtyPerPanel
            };
        }
    }

    public class OutsourceWorkInstructionUploadResultDto
    {
        [JsonPropertyName("file_name")]
        public string FileName { get; set; } = string.Empty;

        [JsonPropertyName("file_path")]
        public string FilePath { get; set; } = string.Empty;

        [JsonPropertyName("content_type")]
        public string? ContentType { get; set; }

        [JsonPropertyName("file_size")]
        public int FileSize { get; set; }

        [JsonPropertyName("uploaded_at")]
        public DateTime UploadedAt { get; set; }
    }

    public class OutsourceWorkInstructionFileCreateRequest
    {
        [JsonPropertyName("file_name")]
        public string FileName { get; set; } = string.Empty;

        [JsonPropertyName("file_path")]
        public string FilePath { get; set; } = string.Empty;

        [JsonPropertyName("content_type")]
        public string? ContentType { get; set; }
    }

    public sealed class OutsourceWorkInstructionGroupItemCreateRequest
    {
        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("cuts_per_sheet")]
        public int CutsPerSheet { get; set; }

        [JsonPropertyName("expected_output_qty")]
        public int? ExpectedOutputQty { get; set; }

        [JsonPropertyName("remark")]
        public string? Remark { get; set; }
    }

    public sealed class OutsourceWorkInstructionGroupCreateRequest
    {
        [JsonPropertyName("group_seq")]
        public int GroupSeq { get; set; }

        [JsonPropertyName("is_bundle")]
        public bool IsBundle { get; set; }

        [JsonPropertyName("sheet_qty")]
        public int SheetQty { get; set; }

        [JsonPropertyName("length_m")]
        public decimal? LengthM { get; set; }

        [JsonPropertyName("sheet_cut_count")]
        public int? SheetCutCount { get; set; }

        [JsonPropertyName("remark")]
        public string? Remark { get; set; }

        [JsonPropertyName("items")]
        public List<OutsourceWorkInstructionGroupItemCreateRequest> Items { get; set; } = new();
    }

    public class OutsourceWorkInstructionCreateRequest
    {
        [JsonPropertyName("instruction_date")]
        public DateTime InstructionDate { get; set; }

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = "CUT";

        [JsonPropertyName("partner_id")]
        public long PartnerId { get; set; }

        [JsonPropertyName("lot_ids")]
        public List<long> LotIds { get; set; } = new();

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("files")]
        public List<OutsourceWorkInstructionFileCreateRequest> Files { get; set; } = new();

        [JsonPropertyName("groups")]
        public List<OutsourceWorkInstructionGroupCreateRequest> Groups { get; set; } = new();
    }

    public class OutsourceWorkInstructionItemDto
    {
        [JsonPropertyName("outsource_work_instruction_item_id")]
        public long OutsourceWorkInstructionItemId { get; set; }

        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string? LotNo { get; set; }

        [JsonPropertyName("order_no")]
        public string? OrderNo { get; set; }

        [JsonPropertyName("line_no")]
        public int? LineNo { get; set; }

        [JsonPropertyName("product_code")]
        public string? ProductCode { get; set; }

        [JsonPropertyName("product_name")]
        public string? ProductName { get; set; }

        [JsonPropertyName("lot_qty")]
        public int? LotQty { get; set; }

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;
    }

    public class OutsourceWorkInstructionDto
    {
        [JsonPropertyName("outsource_work_instruction_id")]
        public long OutsourceWorkInstructionId { get; set; }

        [JsonPropertyName("instruction_no")]
        public string InstructionNo { get; set; } = string.Empty;

        [JsonPropertyName("instruction_date")]
        public DateTime InstructionDate { get; set; }

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;

        [JsonPropertyName("partner_id")]
        public long PartnerId { get; set; }

        [JsonPropertyName("is_bundle")]
        public bool IsBundle { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("items")]
        public List<OutsourceWorkInstructionItemDto> Items { get; set; } = new();

        [JsonPropertyName("files")]
        public List<OutsourceWorkInstructionFileDto> Files { get; set; } = new();
    }

    public class OutsourceWorkInstructionDraftEditModel : ViewModelBase
    {
        private DateTime _instructionDate = DateTime.Today;
        private long _partnerId;
        private string _partnerName = string.Empty;
        private string _memo = string.Empty;
        private decimal? _lengthM;
        private int _sheetQty;
        private int? _sheetCutCount;

        public Guid DraftId { get; set; } = Guid.NewGuid();

        public DateTime InstructionDate
        {
            get => _instructionDate;
            set => SetProperty(ref _instructionDate, value);
        }

        public long PartnerId
        {
            get => _partnerId;
            set => SetProperty(ref _partnerId, value);
        }

        public string PartnerName
        {
            get => _partnerName;
            set => SetProperty(ref _partnerName, value);
        }

        public string Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public decimal? LengthM
        {
            get => _lengthM;
            set
            {
                if (SetProperty(ref _lengthM, value))
                {
                    RecalculateSheetQty();
                }
            }
        }

        public int SheetQty
        {
            get => _sheetQty;
            set => SetProperty(ref _sheetQty, value);
        }

        public int? SheetCutCount
        {
            get => _sheetCutCount;
            set => SetProperty(ref _sheetCutCount, value);
        }

        public List<OutsourceWorkInstructionCandidateLotRowModel> Lots { get; } = new();
        public List<OutsourceWorkInstructionFileCreateRequest> Files { get; } = new();

        public bool IsBundle => Lots.Count > 1;
        public string BundleText => IsBundle ? "묶음" : "개별";
        public string LotSummary => string.Join(", ", Lots.ConvertAll(x => x.LotNo));

        public OutsourceWorkInstructionCandidateLotRowModel? FirstLot => Lots.Count > 0 ? Lots[0] : null;

        public string PlateDataPath => Files.Count > 0 ? Files[0].FilePath : string.Empty;

        public string PlateSize => FirstLot?.PlateSizeText ?? string.Empty;
        public string Spec => FirstLot?.SpecText ?? string.Empty;
        public string CutCountText => FirstLot?.CutCountText ?? string.Empty;

        public void RefreshDerivedValues()
        {
            if (!IsBundle)
            {
                SheetCutCount = FirstLot?.CutQtyPerPanel;
            }

            RecalculateSheetQty();

            OnPropertyChanged(nameof(IsBundle));
            OnPropertyChanged(nameof(BundleText));
            OnPropertyChanged(nameof(LotSummary));
            OnPropertyChanged(nameof(FirstLot));
            OnPropertyChanged(nameof(PlateSize));
            OnPropertyChanged(nameof(Spec));
            OnPropertyChanged(nameof(CutCountText));
        }

        public void Clear()
        {
            DraftId = Guid.NewGuid();
            InstructionDate = DateTime.Today;
            PartnerId = 0;
            PartnerName = string.Empty;
            Memo = string.Empty;
            LengthM = null;
            SheetQty = 0;
            SheetCutCount = null;
            Lots.Clear();
            Files.Clear();
        }

        private void RecalculateSheetQty()
        {
            var panelLengthMm = FirstLot?.PanelLengthMm;

            if (!LengthM.HasValue || !panelLengthMm.HasValue || panelLengthMm.Value <= 0)
            {
                SheetQty = 0;
                return;
            }

            var panelLengthMeter = panelLengthMm.Value / 1000m;
            if (panelLengthMeter <= 0)
            {
                SheetQty = 0;
                return;
            }

            var usableLengthM = LengthM.Value * 0.98m;
            if (usableLengthM <= 0)
            {
                SheetQty = 0;
                return;
            }

            var rawQty = usableLengthM / panelLengthMeter;
            if (rawQty <= 0)
            {
                SheetQty = 0;
                return;
            }

            var roundedQty = Math.Round(rawQty / 5m, 0, MidpointRounding.AwayFromZero) * 5m;
            SheetQty = roundedQty < 0 ? 0 : (int)roundedQty;
        }
    }

    public class OutsourceWorkInstructionBatchGroupCreateRequest
    {
        [JsonPropertyName("partner_id")]
        public long PartnerId { get; set; }

        [JsonPropertyName("lot_ids")]
        public List<long> LotIds { get; set; } = new();

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("files")]
        public List<OutsourceWorkInstructionFileCreateRequest> Files { get; set; } = new();

        [JsonPropertyName("groups")]
        public List<OutsourceWorkInstructionGroupCreateRequest> WorkGroups { get; set; } = new();
    }

    public class OutsourceWorkInstructionBatchCreateRequest
    {
        [JsonPropertyName("instruction_date")]
        public DateTime InstructionDate { get; set; }

        [JsonPropertyName("groups")]
        public List<OutsourceWorkInstructionBatchGroupCreateRequest> Groups { get; set; } = new();
    }

    public class OutsourceWorkInstructionBatchResponseDto
    {
        [JsonPropertyName("items")]
        public List<OutsourceWorkInstructionDto> Items { get; set; } = new();
    }

    public class OutsourcePurchaseOrderTargetDto
    {
        [JsonPropertyName("outsource_work_instruction_id")]
        public long OutsourceWorkInstructionId { get; set; }

        [JsonPropertyName("outsource_work_instruction_item_id")]
        public long OutsourceWorkInstructionItemId { get; set; }

        [JsonPropertyName("instruction_no")]
        public string InstructionNo { get; set; } = string.Empty;

        [JsonPropertyName("instruction_date")]
        public DateTime InstructionDate { get; set; }

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;

        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("is_rework")]
        public bool IsRework { get; set; }

        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("order_no")]
        public string OrderNo { get; set; } = string.Empty;

        [JsonPropertyName("line_no")]
        public int LineNo { get; set; }

        [JsonPropertyName("product_id")]
        public long ProductId { get; set; }

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("outsource_partner_id")]
        public long OutsourcePartnerId { get; set; }

        [JsonPropertyName("outsource_partner_name")]
        public string? OutsourcePartnerName { get; set; }

        [JsonPropertyName("inbound_partner_name")]
        public string InboundPartnerName { get; set; } = string.Empty;

        [JsonPropertyName("is_bundle")]
        public bool IsBundle { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("files")]
        public List<OutsourceWorkInstructionFileDto> Files { get; set; } = new();

        [JsonPropertyName("panel_width_mm")]
        public int? PanelWidthMm { get; set; }

        [JsonPropertyName("panel_length_mm")]
        public int? PanelLengthMm { get; set; }

        [JsonPropertyName("product_spec")]
        public string? ProductSpec { get; set; }

        [JsonPropertyName("cut_qty_per_panel")]
        public int? CutQtyPerPanel { get; set; }

        [JsonPropertyName("length_m")]
        public decimal? LengthM { get; set; }

        [JsonPropertyName("sheet_qty")]
        public int? SheetQty { get; set; }

        [JsonPropertyName("is_print_product")]
        public bool IsPrintProduct { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        public string ReworkText => IsRework ? "재작업" : string.Empty;
        public string BundleText => IsBundle ? "묶음" : "개별";
        public string PlateDataFileName => Files.Count > 0 ? Files[0].FileName : string.Empty;
    }

    public class OutsourcePurchaseOrderTargetListDto
    {
        [JsonPropertyName("items")]
        public List<OutsourcePurchaseOrderTargetDto> Items { get; set; } = new();
    }

    public class OutsourcePurchaseOrderTargetGroupRowModel : ViewModelBase
    {
        public long OutsourceWorkInstructionId { get; set; }
        public string InstructionNo { get; set; } = string.Empty;
        public DateTime InstructionDate { get; set; }
        public string ProcessType { get; set; } = string.Empty;
        public bool IsBundle { get; set; }

        public long OutsourcePartnerId { get; set; }
        public string OutsourcePartnerName { get; set; } = string.Empty;
        public string InboundPartnerName { get; set; } = string.Empty;

        public List<OutsourcePurchaseOrderTargetDto> Items { get; set; } = new();
        public List<OutsourceWorkInstructionFileDto> Files { get; set; } = new();

        public string BundleText => IsBundle ? "묶음" : "개별";
        public string LotSummary => string.Join(", ", Items.ConvertAll(x => x.LotNo));
        public int TotalQty => Items.Sum(x => x.LotQty);
        public string PlateDataFileName => Files.Count > 0 ? Files[0].FileName : string.Empty;
    }

    public class OutsourcePurchaseOrderEditModel : ViewModelBase
    {
        private DateTime _purchaseOrderDate = DateTime.Today;
        private DateTime? _dueDate = DateTime.Today;
        private string _inboundPartnerName = string.Empty;
        private string _outsourcePartnerName = string.Empty;
        private string _remark = string.Empty;
        private string _workDescription = string.Empty;
        private decimal _qty;
        private decimal _unitPrice;
        private decimal _supplyAmount;
        private decimal _vatAmount;
        private decimal _totalAmount;

        public DateTime PurchaseOrderDate
        {
            get => _purchaseOrderDate;
            set => SetProperty(ref _purchaseOrderDate, value);
        }

        public DateTime? DueDate
        {
            get => _dueDate;
            set => SetProperty(ref _dueDate, value);
        }

        public string InboundPartnerName
        {
            get => _inboundPartnerName;
            set => SetProperty(ref _inboundPartnerName, value);
        }

        public string OutsourcePartnerName
        {
            get => _outsourcePartnerName;
            set => SetProperty(ref _outsourcePartnerName, value);
        }

        public string Remark
        {
            get => _remark;
            set => SetProperty(ref _remark, value);
        }

        public string WorkDescription
        {
            get => _workDescription;
            set => SetProperty(ref _workDescription, value);
        }

        public decimal Qty
        {
            get => _qty;
            set
            {
                if (SetProperty(ref _qty, value))
                {
                    Recalculate();
                }
            }
        }

        public decimal UnitPrice
        {
            get => _unitPrice;
            set
            {
                if (SetProperty(ref _unitPrice, value))
                {
                    Recalculate();
                }
            }
        }

        public decimal SupplyAmount
        {
            get => _supplyAmount;
            set => SetProperty(ref _supplyAmount, value);
        }

        public decimal VatAmount
        {
            get => _vatAmount;
            set => SetProperty(ref _vatAmount, value);
        }

        public decimal TotalAmount
        {
            get => _totalAmount;
            set => SetProperty(ref _totalAmount, value);
        }

        public void LoadFromGroup(OutsourcePurchaseOrderTargetGroupRowModel group)
        {
            PurchaseOrderDate = DateTime.Today;
            DueDate = DateTime.Today;
            InboundPartnerName = group.InboundPartnerName;
            OutsourcePartnerName = group.OutsourcePartnerName;
            Qty = group.TotalQty;
            WorkDescription = group.ProcessType == "CUT" ? "재단 외주 작업" : "인쇄 외주 작업";
            Remark = string.Empty;
        }

        public void Clear()
        {
            PurchaseOrderDate = DateTime.Today;
            DueDate = DateTime.Today;
            InboundPartnerName = string.Empty;
            OutsourcePartnerName = string.Empty;
            Remark = string.Empty;
            WorkDescription = string.Empty;
            Qty = 0;
            UnitPrice = 0;
            SupplyAmount = 0;
            VatAmount = 0;
            TotalAmount = 0;
        }

        private void Recalculate()
        {
            SupplyAmount = Qty * UnitPrice;
            VatAmount = Math.Round(SupplyAmount * 0.1m, 0, MidpointRounding.AwayFromZero);
            TotalAmount = SupplyAmount + VatAmount;
        }

        public class OutsourcePurchaseOrderBundleRowModel : ViewModelBase
        {
            public string BundleType { get; set; } = string.Empty;
            public string Title { get; set; } = string.Empty;

            public List<OutsourcePurchaseOrderTargetGroupRowModel> Groups { get; set; } = new();
            public List<OutsourcePurchaseOrderTargetDto> Items { get; set; } = new();
            public List<OutsourceWorkInstructionFileDto> Files { get; set; } = new();

            public string LotSummary => string.Join(Environment.NewLine, Items.Select(x => x.LotNo).Distinct());
            public int LotCount => Items.Select(x => x.LotNo).Distinct().Count();
            public int TotalQty => Items.Sum(x => x.LotQty);

            public string ProcessType => BundleType;
        }
    }

    public class OutsourceCutPurchaseOrderItemEditModel : ViewModelBase
    {
        private int _no;
        private string _rawMaterialText = string.Empty;
        private decimal? _lengthM;
        private string _inboundPlaceName = string.Empty;
        private string _sourcePartnerName = string.Empty;
        private string _cutSpec = string.Empty;
        private int? _sheetQty;
        private int? _panelLengthMm;
        private decimal? _savedLengthM;
        private int? _savedSheetQty;

        public long SourceOutsourceWorkInstructionId { get; set; }

        public List<long> LotIds { get; } = new();

        public string LotSummary { get; set; } = string.Empty;

        public bool IsBundle { get; set; }
        public decimal? SavedLengthM
{
    get => _savedLengthM;
    set
    {
        if (SetProperty(ref _savedLengthM, value))
        {
            OnPropertyChanged(nameof(LengthMDisplay));
        }
    }
}

public int? SavedSheetQty
{
    get => _savedSheetQty;
    set
    {
        if (SetProperty(ref _savedSheetQty, value))
        {
            OnPropertyChanged(nameof(SheetQtyDisplay));
        }
    }
}

public string LengthMDisplay => SavedLengthM?.ToString("0.##") ?? string.Empty;

public string SheetQtyDisplay => SavedSheetQty?.ToString() ?? string.Empty;

        public int No
        {
            get => _no;
            set => SetProperty(ref _no, value);
        }

        public string RawMaterialText
        {
            get => _rawMaterialText;
            set => SetProperty(ref _rawMaterialText, value);
        }

        public decimal? LengthM
        {
            get => _lengthM;
            set
            {
                if (SetProperty(ref _lengthM, value))
                {
                    RecalculateSheetQty();
                }
            }
        }

        public string InboundPlaceName
        {
            get => _inboundPlaceName;
            set
            {
                if (SetProperty(ref _inboundPlaceName, value))
                {
                    OnPropertyChanged(nameof(InboundPlaceDisplay));
                }
            }
        }

        public string SourcePartnerName
        {
            get => _sourcePartnerName;
            set
            {
                if (SetProperty(ref _sourcePartnerName, value))
                {
                    OnPropertyChanged(nameof(InboundPlaceDisplay));
                }
            }
        }

        public string InboundPlaceDisplay
        {
            get
            {
                if (string.IsNullOrWhiteSpace(SourcePartnerName))
                {
                    return InboundPlaceName;
                }

                return $"{InboundPlaceName}({SourcePartnerName})";
            }
        }

        public string CutSpec
        {
            get => _cutSpec;
            set => SetProperty(ref _cutSpec, value);
        }

        public int? SheetQty
        {
            get => _sheetQty;
            set => SetProperty(ref _sheetQty, value);
        }

        public int? PanelLengthMm
        {
            get => _panelLengthMm;
            set
            {
                if (SetProperty(ref _panelLengthMm, value))
                {
                    RecalculateSheetQty();
                }
            }
        }

        private void RecalculateSheetQty()
        {
            if (!LengthM.HasValue || !PanelLengthMm.HasValue || PanelLengthMm.Value <= 0)
            {
                SheetQty = null;
                return;
            }

            var panelLengthMeter = PanelLengthMm.Value / 1000m;
            if (panelLengthMeter <= 0)
            {
                SheetQty = null;
                return;
            }

            var usableLengthM = LengthM.Value * 0.98m;
            if (usableLengthM <= 0)
            {
                SheetQty = 0;
                return;
            }

            var rawQty = usableLengthM / panelLengthMeter;
            if (rawQty <= 0)
            {
                SheetQty = 0;
                return;
            }

            var roundedQty = Math.Round(rawQty / 5m, 0, MidpointRounding.AwayFromZero) * 5m;

            SheetQty = roundedQty < 0 ? 0 : (int)roundedQty;
        }
    }

    public class OutsourceCutPurchaseOrderEditModel : ViewModelBase
    {
        private string _title = "가공의뢰서_재단";
        private string _companyName = "코리아 라벨";
        private string _requestPartnerName = "세미산업";
        private string _requesterName = "김완준";
        private DateTime _requestDate = DateTime.Today;
        private string _rawMaterialInboundText = string.Empty;
        private decimal? _stock500Width;
        private decimal? _stock600Width;
        private decimal? _stock600Tpt0268;
        private string _remark = string.Empty;

        public ObservableCollection<OutsourceCutPurchaseOrderItemEditModel> Items { get; } = new();

        public string Title
        {
            get => _title;
            set => SetProperty(ref _title, value);
        }

        public string CompanyName
        {
            get => _companyName;
            set => SetProperty(ref _companyName, value);
        }

        public string RequestPartnerName
        {
            get => _requestPartnerName;
            set => SetProperty(ref _requestPartnerName, value);
        }

        public string RequesterName
        {
            get => _requesterName;
            set => SetProperty(ref _requesterName, value);
        }

        public DateTime RequestDate
        {
            get => _requestDate;
            set => SetProperty(ref _requestDate, value);
        }

        public string RawMaterialInboundText
        {
            get => _rawMaterialInboundText;
            set => SetProperty(ref _rawMaterialInboundText, value);
        }

        public decimal? Stock500Width
        {
            get => _stock500Width;
            set => SetProperty(ref _stock500Width, value);
        }

        public decimal? Stock600Width
        {
            get => _stock600Width;
            set => SetProperty(ref _stock600Width, value);
        }

        public decimal? Stock600Tpt0268
        {
            get => _stock600Tpt0268;
            set => SetProperty(ref _stock600Tpt0268, value);
        }

        public string Remark
        {
            get => _remark;
            set => SetProperty(ref _remark, value);
        }

        public void LoadFromBundle(OutsourcePurchaseOrderBundleRowModel bundle)
        {
            CompanyName = "코리아 라벨";
            RequestPartnerName = "세미산업";
            RequesterName = "김완준";
            RequestDate = DateTime.Today;
            RawMaterialInboundText = string.Empty;
            Remark = string.Empty;

            Items.Clear();

            var index = 1;

            foreach (var group in bundle.Groups.OrderBy(x => x.InstructionDate).ThenBy(x => x.InstructionNo))
            {
                var firstItem = group.Items.FirstOrDefault();
                if (firstItem == null)
                {
                    continue;
                }

                var rawMaterialText = firstItem.PanelWidthMm.HasValue
                    ? $"{firstItem.PanelWidthMm.Value}폭"
                    : string.Empty;

                var cutSpec = firstItem.PanelWidthMm.HasValue && firstItem.PanelLengthMm.HasValue
                    ? $"{firstItem.PanelWidthMm.Value} x {firstItem.PanelLengthMm.Value}"
                    : string.Empty;

                var inboundPlaces = group.Items
                    .Select(x => x.IsPrintProduct ? "상림" : "보현")
                    .Distinct()
                    .ToList();

                var inboundPlaceName = string.Join(", ", inboundPlaces);

                var sourcePartners = group.Items
                    .Select(x => x.PartnerName)
                    .Where(x => !string.IsNullOrWhiteSpace(x))
                    .Distinct()
                    .ToList();

                var sourcePartnerName = string.Join(", ", sourcePartners!);

                var lotSummary = string.Join(", ",
                    group.Items
                        .Select(x => x.LotNo)
                        .Where(x => !string.IsNullOrWhiteSpace(x))
                        .Distinct());

                var row = new OutsourceCutPurchaseOrderItemEditModel
                {
                    No = index++,
                    SourceOutsourceWorkInstructionId = group.OutsourceWorkInstructionId,
                    LotSummary = lotSummary,
                    IsBundle = group.IsBundle,
                    RawMaterialText = rawMaterialText,
                    PanelLengthMm = firstItem.PanelLengthMm,
                    LengthM = null,
                    SavedLengthM = firstItem.LengthM,
                    InboundPlaceName = inboundPlaceName,
                    SourcePartnerName = sourcePartnerName,
                    CutSpec = cutSpec,
                    SheetQty = null,
                    SavedSheetQty = firstItem.SheetQty
                };

                foreach (var lotId in group.Items.Select(x => x.LotId).Distinct())
                {
                    row.LotIds.Add(lotId);
                }

                Items.Add(row);
            }
        }

        public void Clear()
        {
            CompanyName = "코리아 라벨";
            RequestPartnerName = "세미산업";
            RequesterName = "김완준";
            RequestDate = DateTime.Today;
            RawMaterialInboundText = string.Empty;
            Stock500Width = null;
            Stock600Width = null;
            Stock600Tpt0268 = null;
            Remark = string.Empty;
            Items.Clear();
        }
    }
}