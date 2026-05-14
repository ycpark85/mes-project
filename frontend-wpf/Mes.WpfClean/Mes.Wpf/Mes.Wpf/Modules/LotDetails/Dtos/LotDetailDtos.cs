using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.LotDetails.Dtos
{
    public class LotTraceDetailDto
    {
        [JsonPropertyName("progress")]
        public LotTraceProgressDto Progress { get; set; } = new();

        [JsonPropertyName("lot_basic")]
        public LotTraceBasicDto LotBasic { get; set; } = new();

        [JsonPropertyName("product_order")]
        public LotTraceProductOrderDto ProductOrder { get; set; } = new();

        [JsonPropertyName("outsource_works")]
        public List<LotTraceOutsourceWorkDto> OutsourceWorks { get; set; } = new();

        [JsonPropertyName("inspection")]
        public LotTraceInspectionDto? Inspection { get; set; }
    }

    public class LotTraceProgressDto
    {
        [JsonPropertyName("lot_created")]
        public bool LotCreated { get; set; }

        [JsonPropertyName("outsource_instruction_created")]
        public bool OutsourceInstructionCreated { get; set; }

        [JsonPropertyName("outsource_work_done")]
        public bool OutsourceWorkDone { get; set; }

        [JsonPropertyName("inspection_done")]
        public bool InspectionDone { get; set; }
    }

    public class LotTraceBasicDto
    {
        [JsonPropertyName("lot_id")]
        public int LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string? LotNo { get; set; }

        [JsonPropertyName("status")]
        public string? Status { get; set; }

        [JsonPropertyName("is_rework")]
        public bool IsRework { get; set; }

        [JsonPropertyName("parent_lot_id")]
        public int? ParentLotId { get; set; }

        [JsonPropertyName("parent_lot_no")]
        public string? ParentLotNo { get; set; }

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("uom")]
        public string? Uom { get; set; }

        [JsonPropertyName("created_date")]
        public DateTime CreatedDate { get; set; }

        [JsonPropertyName("due_date")]
        public DateTime DueDate { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class LotTraceProductOrderDto
    {
        [JsonPropertyName("order_line_id")]
        public int OrderLineId { get; set; }

        [JsonPropertyName("order_no")]
        public string? OrderNo { get; set; }

        [JsonPropertyName("line_no")]
        public int LineNo { get; set; }

        [JsonPropertyName("partner_id")]
        public int PartnerId { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("product_id")]
        public int ProductId { get; set; }

        [JsonPropertyName("product_code")]
        public string? ProductCode { get; set; }

        [JsonPropertyName("product_name")]
        public string? ProductName { get; set; }

        [JsonPropertyName("product_spec")]
        public string? ProductSpec { get; set; }

        [JsonPropertyName("panel_width_mm")]
        public int? PanelWidthMm { get; set; }

        [JsonPropertyName("panel_length_mm")]
        public int? PanelLengthMm { get; set; }

        [JsonPropertyName("cut_qty_per_panel")]
        public int? CutQtyPerPanel { get; set; }

        [JsonPropertyName("current_stock_qty")]
        public int CurrentStockQty { get; set; }

        [JsonPropertyName("order_qty")]
        public int OrderQty { get; set; }

        [JsonPropertyName("order_date")]
        public DateTime OrderDate { get; set; }

        [JsonPropertyName("due_date")]
        public DateTime DueDate { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class LotTraceOutsourceWorkDto
    {
        [JsonPropertyName("outsource_work_group_id")]
        public int OutsourceWorkGroupId { get; set; }

        [JsonPropertyName("outsource_work_group_item_id")]
        public int OutsourceWorkGroupItemId { get; set; }

        [JsonPropertyName("outsource_work_instruction_id")]
        public int OutsourceWorkInstructionId { get; set; }

        [JsonPropertyName("instruction_no")]
        public string? InstructionNo { get; set; }

        [JsonPropertyName("instruction_date")]
        public DateTime InstructionDate { get; set; }

        [JsonPropertyName("process_type")]
        public string? ProcessType { get; set; }

        [JsonPropertyName("group_seq")]
        public string? GroupSeq { get; set; }

        [JsonPropertyName("is_bundle")]
        public bool IsBundle { get; set; }

        [JsonPropertyName("fabric_lot_no")]
        public string? FabricLotNo { get; set; }

        [JsonPropertyName("length_m")]
        public decimal? LengthM { get; set; }

        [JsonPropertyName("sheet_qty")]
        public int SheetQty { get; set; }

        [JsonPropertyName("sheet_cut_count")]
        public int SheetCutCount { get; set; }

        [JsonPropertyName("cuts_per_sheet")]
        public int CutsPerSheet { get; set; }

        [JsonPropertyName("expected_output_qty")]
        public int? ExpectedOutputQty { get; set; }

        [JsonPropertyName("group_expected_output_qty")]
        public int GroupExpectedOutputQty { get; set; }

        [JsonPropertyName("work_done_sheet_qty")]
        public int? WorkDoneSheetQty { get; set; }

        [JsonPropertyName("confirmed_outsource_qty")]
        public int? ConfirmedOutsourceQty { get; set; }

        [JsonPropertyName("status")]
        public string? Status { get; set; }

        [JsonPropertyName("vendor_received_at")]
        public DateTime? VendorReceivedAt { get; set; }

        [JsonPropertyName("work_done_at")]
        public DateTime? WorkDoneAt { get; set; }

        [JsonPropertyName("shipped_at")]
        public DateTime? ShippedAt { get; set; }

        [JsonPropertyName("remark")]
        public string? Remark { get; set; }

        [JsonPropertyName("work_done_remark")]
        public string? WorkDoneRemark { get; set; }
    }

    public class LotTraceInspectionDto
    {
        [JsonPropertyName("inspection_schedule_id")]
        public int? InspectionScheduleId { get; set; }

        [JsonPropertyName("inspection_date")]
        public DateTime? InspectionDate { get; set; }

        [JsonPropertyName("schedule_status")]
        public string? ScheduleStatus { get; set; }

        [JsonPropertyName("received_at")]
        public DateTime? ReceivedAt { get; set; }

        [JsonPropertyName("started_at")]
        public DateTime? StartedAt { get; set; }

        [JsonPropertyName("finished_at")]
        public DateTime? FinishedAt { get; set; }

        [JsonPropertyName("inspection_result_id")]
        public int? InspectionResultId { get; set; }

        [JsonPropertyName("inspected_qty")]
        public int? InspectedQty { get; set; }

        [JsonPropertyName("good_qty")]
        public int? GoodQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int? DefectQty { get; set; }

        [JsonPropertyName("defect_ship_qty")]
        public int? DefectShipQty { get; set; }

        [JsonPropertyName("is_partial")]
        public bool? IsPartial { get; set; }

        [JsonPropertyName("next_inspection_date")]
        public DateTime? NextInspectionDate { get; set; }

        [JsonPropertyName("partial_reason")]
        public string? PartialReason { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("created_by")]
        public string? CreatedBy { get; set; }

        [JsonPropertyName("result_created_at")]
        public DateTime? ResultCreatedAt { get; set; }

        [JsonPropertyName("defects")]
        public List<LotTraceInspectionDefectDto> Defects { get; set; } = new();
    }

    public class LotTraceInspectionDefectDto
    {
        [JsonPropertyName("inspection_defect_id")]
        public int InspectionDefectId { get; set; }

        [JsonPropertyName("defect_type_id")]
        public int DefectTypeId { get; set; }

        [JsonPropertyName("defect_type_code")]
        public string? DefectTypeCode { get; set; }

        [JsonPropertyName("defect_type_name")]
        public string? DefectTypeName { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("disposition")]
        public string? Disposition { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("attachments")]
        public List<LotTraceDefectAttachmentDto> Attachments { get; set; } = new();

        [JsonIgnore]
        public LotTraceDefectAttachmentDto? FirstAttachment => Attachments.FirstOrDefault();

        [JsonIgnore]
        public string? FirstAttachmentImageUrl => FirstAttachment?.ImageUrl;

        [JsonIgnore]
        public bool HasAttachment => !string.IsNullOrWhiteSpace(FirstAttachmentImageUrl);

        [JsonIgnore]
        public string AttachmentDisplayText => HasAttachment ? "이미지" : "없음";
    }

    public class LotTraceDefectAttachmentDto
    {
        [JsonPropertyName("inspection_defect_attachment_id")]
        public int InspectionDefectAttachmentId { get; set; }

        [JsonPropertyName("file_uri")]
        public string FileUri { get; set; } = string.Empty;

        [JsonPropertyName("file_name")]
        public string? FileName { get; set; }

        [JsonPropertyName("mime_type")]
        public string? MimeType { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("image_url")]
        public string? ImageUrl { get; set; }
    }

}