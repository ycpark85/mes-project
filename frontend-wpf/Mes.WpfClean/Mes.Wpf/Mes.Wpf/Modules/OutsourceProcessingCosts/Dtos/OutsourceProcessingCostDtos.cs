using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.Dtos
{
    public class OutsourceProcessingCostTargetListDto
    {
        [JsonPropertyName("items")]
        public List<OutsourceProcessingCostTargetDto> Items { get; set; } = new();
    }

    public class OutsourceProcessingCostTargetDto
    {
        [JsonPropertyName("target_key")]
        public string TargetKey { get; set; } = string.Empty;

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;

        [JsonPropertyName("outsource_work_group_id")]
        public long? OutsourceWorkGroupId { get; set; }

        [JsonPropertyName("lot_id")]
        public long? LotId { get; set; }

        [JsonPropertyName("instruction_no")]
        public string? InstructionNo { get; set; }

        [JsonPropertyName("instruction_date")]
        public DateTime? InstructionDate { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("group_seq")]
        public string? GroupSeq { get; set; }

        [JsonPropertyName("is_bundle")]
        public bool IsBundle { get; set; }

        [JsonPropertyName("lot_count")]
        public int LotCount { get; set; }

        [JsonPropertyName("representative_lot_id")]
        public long? RepresentativeLotId { get; set; }

        [JsonPropertyName("representative_lot_no")]
        public string? RepresentativeLotNo { get; set; }

        [JsonPropertyName("representative_product_name")]
        public string? RepresentativeProductName { get; set; }

        [JsonPropertyName("lot_nos")]
        public List<string> LotNos { get; set; } = new();

        [JsonPropertyName("product_names")]
        public List<string> ProductNames { get; set; } = new();

        [JsonPropertyName("product_specs")]
        public List<string> ProductSpecs { get; set; } = new();

        [JsonPropertyName("sheet_qty")]
        public long? SheetQty { get; set; }

        [JsonPropertyName("instruction_output_qty")]
        public long? InstructionOutputQty { get; set; }

        [JsonPropertyName("allocation_basis_type")]
        public string AllocationBasisType { get; set; } = string.Empty;

        [JsonPropertyName("allocation_basis_value")]
        public decimal AllocationBasisValue { get; set; }

        [JsonPropertyName("outsource_processing_cost_group_id")]
        public long? OutsourceProcessingCostGroupId { get; set; }

        [JsonPropertyName("already_cost_group_no")]
        public string? AlreadyCostGroupNo { get; set; }

        [JsonPropertyName("cost_status")]
        public string? CostStatus { get; set; }

        [JsonPropertyName("standard_amount")]
        public decimal? StandardAmount { get; set; }

        [JsonPropertyName("actual_amount")]
        public decimal? ActualAmount { get; set; }

        [JsonPropertyName("amount_difference")]
        public decimal? AmountDifference { get; set; }

        [JsonPropertyName("settlement_month")]
        public DateTime? SettlementMonth { get; set; }

        [JsonPropertyName("allocations")]
        public List<OutsourceProcessingCostAllocationDto> Allocations { get; set; } = new();
    }

    public class OutsourceProcessingCostGroupListDto
    {
        [JsonPropertyName("items")]
        public List<OutsourceProcessingCostGroupDto> Items { get; set; } = new();

        [JsonPropertyName("total_count")]
        public int TotalCount { get; set; }

        [JsonPropertyName("standard_total")]
        public decimal StandardTotal { get; set; }

        [JsonPropertyName("actual_total")]
        public decimal ActualTotal { get; set; }

        [JsonPropertyName("difference_total")]
        public decimal DifferenceTotal { get; set; }

        [JsonPropertyName("unclosed_count")]
        public int UnclosedCount { get; set; }
    }

    public class OutsourceProcessingCostGroupDto
    {
        [JsonPropertyName("outsource_processing_cost_group_id")]
        public long OutsourceProcessingCostGroupId { get; set; }

        [JsonPropertyName("cost_group_no")]
        public string CostGroupNo { get; set; } = string.Empty;

        [JsonPropertyName("settlement_month")]
        public DateTime SettlementMonth { get; set; }

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("work_group_count")]
        public int WorkGroupCount { get; set; }

        [JsonPropertyName("lot_count")]
        public int LotCount { get; set; }

        [JsonPropertyName("partner_names")]
        public List<string> PartnerNames { get; set; } = new();

        [JsonPropertyName("instruction_nos")]
        public List<string> InstructionNos { get; set; } = new();

        [JsonPropertyName("lot_nos")]
        public List<string> LotNos { get; set; } = new();

        [JsonPropertyName("product_names")]
        public List<string> ProductNames { get; set; } = new();

        [JsonPropertyName("standard_amount")]
        public decimal? StandardAmount { get; set; }

        [JsonPropertyName("actual_amount")]
        public decimal? ActualAmount { get; set; }

        [JsonPropertyName("amount_difference")]
        public decimal? AmountDifference { get; set; }

        [JsonPropertyName("standard_memo")]
        public string? StandardMemo { get; set; }

        [JsonPropertyName("actual_billing_month")]
        public DateTime? ActualBillingMonth { get; set; }

        [JsonPropertyName("actual_memo")]
        public string? ActualMemo { get; set; }

        [JsonPropertyName("remark")]
        public string? Remark { get; set; }

        [JsonPropertyName("closed_at")]
        public DateTime? ClosedAt { get; set; }

        [JsonPropertyName("canceled_at")]
        public DateTime? CanceledAt { get; set; }

        [JsonPropertyName("allocations")]
        public List<OutsourceProcessingCostAllocationDto> Allocations { get; set; } = new();
    }

    public class OutsourceProcessingCostAllocationDto
    {
        [JsonPropertyName("outsource_processing_cost_allocation_id")]
        public long? OutsourceProcessingCostAllocationId { get; set; }

        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

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

        [JsonPropertyName("cuts_per_sheet")]
        public int? CutsPerSheet { get; set; }

        [JsonPropertyName("sheet_qty")]
        public long? SheetQty { get; set; }

        [JsonPropertyName("instruction_output_qty")]
        public long? InstructionOutputQty { get; set; }

        [JsonPropertyName("basis_type")]
        public string BasisType { get; set; } = string.Empty;

        [JsonPropertyName("basis_value")]
        public decimal BasisValue { get; set; }

        [JsonPropertyName("basis_area_sqm")]
        public decimal? BasisAreaSqm { get; set; }

        [JsonPropertyName("allocation_ratio")]
        public decimal AllocationRatio { get; set; }

        [JsonPropertyName("standard_allocated_amount")]
        public decimal? StandardAllocatedAmount { get; set; }

        [JsonPropertyName("actual_allocated_amount")]
        public decimal? ActualAllocatedAmount { get; set; }

        [JsonPropertyName("amount_difference")]
        public decimal? AmountDifference { get; set; }
    }

    public class OutsourceProcessingCostSaveRequest
    {
        [JsonPropertyName("settlement_month")]
        public DateTime SettlementMonth { get; set; }

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;

        [JsonPropertyName("target_work_group_ids")]
        public List<long> TargetWorkGroupIds { get; set; } = new();

        [JsonPropertyName("target_lot_ids")]
        public List<long> TargetLotIds { get; set; } = new();

        [JsonPropertyName("standard_amount")]
        public decimal? StandardAmount { get; set; }

        [JsonPropertyName("standard_memo")]
        public string? StandardMemo { get; set; }

        [JsonPropertyName("actual_amount")]
        public decimal? ActualAmount { get; set; }

        [JsonPropertyName("actual_billing_month")]
        public DateTime? ActualBillingMonth { get; set; }

        [JsonPropertyName("actual_memo")]
        public string? ActualMemo { get; set; }

        [JsonPropertyName("remark")]
        public string? Remark { get; set; }
    }
}
