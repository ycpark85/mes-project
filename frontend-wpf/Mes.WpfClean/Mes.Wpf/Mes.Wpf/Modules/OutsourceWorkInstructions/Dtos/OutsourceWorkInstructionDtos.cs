using Mes.Wpf.Core.Common;
using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;
using System.Linq;


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
    }

    public class OutsourceWorkInstructionCandidateLotListDto
    {
        [JsonPropertyName("items")]
        public List<OutsourceWorkInstructionCandidateLotDto> Items { get; set; } = new();
    }

    public class OutsourceWorkInstructionCandidateLotRowModel : ViewModelBase
    {
        private bool _isSelected;

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
                AvailableProcessTypes = dto.AvailableProcessTypes ?? new List<string>()
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

        public List<OutsourceWorkInstructionCandidateLotRowModel> Lots { get; } = new();
        public List<OutsourceWorkInstructionFileCreateRequest> Files { get; } = new();

        public bool IsBundle => Lots.Count > 1;
        public string BundleText => IsBundle ? "묶음" : "개별";
        public string LotSummary => string.Join(", ", Lots.ConvertAll(x => x.LotNo));

        public void Clear()
        {
            DraftId = Guid.NewGuid();
            InstructionDate = DateTime.Today;
            PartnerId = 0;
            PartnerName = string.Empty;
            Memo = string.Empty;
            Lots.Clear();
            Files.Clear();
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
    }



}