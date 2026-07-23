using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.RawMaterials.Dtos
{
    public static class SelfUseSheetDisplay
    {
        public static string Purpose(string? code) => code switch
        {
            "PRINT_SETUP" => "인쇄 초기 셋팅",
            "SAMPLE" => "샘플 제작",
            "TEST_RND" => "시험/개발",
            "OTHER" => "기타",
            _ => code ?? string.Empty
        };

        public static string Execution(string? code) => code switch
        {
            "INTERNAL" => "내부 재단",
            "OUTSOURCE" => "외주 재단",
            _ => code ?? string.Empty
        };

        public static string JobStatus(string? code) => code switch
        {
            "DRAFT" => "임시저장",
            "IN_PROGRESS" => "가공중",
            "COMPLETED" => "완료",
            "CANCELED" => "취소",
            _ => code ?? string.Empty
        };

        public static string InventoryStatus(string? code) => code switch
        {
            "AVAILABLE" => "사용가능",
            "DEPLETED" => "소진",
            "CANCELED" => "취소",
            _ => code ?? string.Empty
        };

        public static string Movement(string? code) => code switch
        {
            "TRANSFER_OUT" => "위치이동 출고",
            "TRANSFER_IN" => "위치이동 입고",
            "WORK_USE_OUT" => "외주작업 투입",
            "WORK_USE_REVERSE" => "외주작업 투입취소",
            "PRODUCE_IN" => "재단완료 입고",
            "USE_OUT" => "사용",
            "USE_REVERSE" => "사용취소",
            "CANCEL_OUT" => "완료취소",
            _ => code ?? string.Empty
        };
    }

    public sealed class SelfUseSheetOption
    {
        public SelfUseSheetOption(string code, string name)
        {
            Code = code;
            Name = name;
        }

        public string Code { get; }
        public string Name { get; }
    }

    public class SelfUseSheetAllocationDto
    {
        [JsonPropertyName("self_use_sheet_raw_material_allocation_id")]
        public long AllocationId { get; set; }

        [JsonPropertyName("raw_material_id")]
        public long RawMaterialId { get; set; }

        [JsonPropertyName("material_code")]
        public string MaterialCode { get; set; } = string.Empty;

        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = string.Empty;

        [JsonPropertyName("source_location_name")]
        public string SourceLocationName { get; set; } = string.Empty;

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("planned_qty")]
        public decimal PlannedQty { get; set; }

        [JsonPropertyName("actual_consumed_qty")]
        public decimal? ActualConsumedQty { get; set; }

        [JsonPropertyName("returned_qty")]
        public decimal ReturnedQty { get; set; }

        [JsonPropertyName("unit_cost_snapshot")]
        public decimal? UnitCostSnapshot { get; set; }

        [JsonPropertyName("amount_snapshot")]
        public decimal? AmountSnapshot { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;
    }

    public class SelfUseSheetJobDto
    {
        [JsonPropertyName("self_use_sheet_job_id")]
        public long SelfUseSheetJobId { get; set; }

        [JsonPropertyName("use_no")]
        public string UseNo { get; set; } = string.Empty;

        [JsonPropertyName("purpose_type")]
        public string PurposeType { get; set; } = string.Empty;
        public string PurposeDisplay => SelfUseSheetDisplay.Purpose(PurposeType);

        [JsonPropertyName("execution_type")]
        public string ExecutionType { get; set; } = string.Empty;
        public string ExecutionDisplay => SelfUseSheetDisplay.Execution(ExecutionType);

        [JsonPropertyName("partner_id")]
        public long? PartnerId { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;
        public string StatusDisplay => SelfUseSheetDisplay.JobStatus(Status);

        [JsonPropertyName("cut_width_mm")]
        public decimal CutWidthMm { get; set; }

        [JsonPropertyName("cut_length_mm")]
        public decimal CutLengthMm { get; set; }
        public string CutSpecDisplay => $"{CutWidthMm:N0} × {CutLengthMm:N0} mm";

        [JsonPropertyName("planned_output_qty")]
        public long PlannedOutputQty { get; set; }

        [JsonPropertyName("expected_processing_fee")]
        public decimal ExpectedProcessingFee { get; set; }

        [JsonPropertyName("actual_processing_fee")]
        public decimal? ActualProcessingFee { get; set; }

        [JsonPropertyName("actual_input_qty")]
        public decimal? ActualInputQty { get; set; }

        [JsonPropertyName("produced_qty")]
        public long? ProducedQty { get; set; }

        [JsonPropertyName("scrap_qty")]
        public long? ScrapQty { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("cancel_reason")]
        public string? CancelReason { get; set; }

        [JsonPropertyName("version")]
        public int Version { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("started_at")]
        public DateTime? StartedAt { get; set; }

        [JsonPropertyName("completed_at")]
        public DateTime? CompletedAt { get; set; }

        [JsonPropertyName("sheet_lot_id")]
        public long? SheetLotId { get; set; }

        [JsonPropertyName("sheet_lot_no")]
        public string? SheetLotNo { get; set; }

        [JsonPropertyName("allocations")]
        public List<SelfUseSheetAllocationDto> Allocations { get; set; } = new();
    }

    public class SelfUseSheetJobListDto
    {
        [JsonPropertyName("items")]
        public List<SelfUseSheetJobDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }
    }

    public class SelfUseSheetAllocationCreateRequest
    {
        [JsonPropertyName("raw_material_inventory_lot_id")]
        public long RawMaterialInventoryLotId { get; set; }

        [JsonPropertyName("planned_qty")]
        public decimal PlannedQty { get; set; }
    }

    public class SelfUseSheetJobCreateRequest
    {
        [JsonPropertyName("purpose_type")]
        public string PurposeType { get; set; } = string.Empty;

        [JsonPropertyName("execution_type")]
        public string ExecutionType { get; set; } = string.Empty;

        [JsonPropertyName("partner_id")]
        public long? PartnerId { get; set; }

        [JsonPropertyName("cut_width_mm")]
        public decimal CutWidthMm { get; set; }

        [JsonPropertyName("cut_length_mm")]
        public decimal CutLengthMm { get; set; }

        [JsonPropertyName("planned_output_qty")]
        public long PlannedOutputQty { get; set; }

        [JsonPropertyName("expected_processing_fee")]
        public decimal ExpectedProcessingFee { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("allocations")]
        public List<SelfUseSheetAllocationCreateRequest> Allocations { get; set; } = new();
    }

    public class SelfUseSheetJobStartRequest
    {
        [JsonPropertyName("expected_version")]
        public int ExpectedVersion { get; set; }
    }

    public class SelfUseSheetAllocationCompleteRequest
    {
        [JsonPropertyName("allocation_id")]
        public long AllocationId { get; set; }

        [JsonPropertyName("actual_consumed_qty")]
        public decimal ActualConsumedQty { get; set; }

        [JsonPropertyName("returned_qty")]
        public decimal ReturnedQty { get; set; }
    }

    public class SelfUseSheetJobCompleteRequest
    {
        [JsonPropertyName("expected_version")]
        public int ExpectedVersion { get; set; }

        [JsonPropertyName("produced_qty")]
        public long ProducedQty { get; set; }

        [JsonPropertyName("scrap_qty")]
        public long ScrapQty { get; set; }

        [JsonPropertyName("actual_processing_fee")]
        public decimal ActualProcessingFee { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("allocations")]
        public List<SelfUseSheetAllocationCompleteRequest> Allocations { get; set; } = new();
    }

    public class SelfUseSheetJobCancelRequest
    {
        [JsonPropertyName("expected_version")]
        public int ExpectedVersion { get; set; }

        [JsonPropertyName("reason")]
        public string Reason { get; set; } = string.Empty;
    }

    public class SelfUseSheetInventoryLotDto
    {
        [JsonPropertyName("self_use_sheet_inventory_lot_id")]
        public long SelfUseSheetInventoryLotId { get; set; }

        [JsonPropertyName("self_use_sheet_job_id")]
        public long SelfUseSheetJobId { get; set; }

        [JsonPropertyName("use_no")]
        public string UseNo { get; set; } = string.Empty;

        [JsonPropertyName("purpose_type")]
        public string PurposeType { get; set; } = string.Empty;
        public string PurposeDisplay => SelfUseSheetDisplay.Purpose(PurposeType);

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("raw_material_id")]
        public long RawMaterialId { get; set; }

        [JsonPropertyName("material_code")]
        public string MaterialCode { get; set; } = string.Empty;

        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("sheet_lot_no")]
        public string SheetLotNo { get; set; } = string.Empty;

        [JsonPropertyName("source_lot_summary")]
        public string SourceLotSummary { get; set; } = string.Empty;

        [JsonPropertyName("cut_width_mm")]
        public decimal CutWidthMm { get; set; }

        [JsonPropertyName("cut_length_mm")]
        public decimal CutLengthMm { get; set; }
        public string CutSpecDisplay => $"{CutWidthMm:N0} × {CutLengthMm:N0} mm";

        [JsonPropertyName("initial_qty")]
        public long InitialQty { get; set; }

        [JsonPropertyName("used_qty")]
        public long UsedQty { get; set; }

        [JsonPropertyName("current_qty")]
        public long CurrentQty { get; set; }

        [JsonPropertyName("material_amount")]
        public decimal MaterialAmount { get; set; }

        [JsonPropertyName("processing_fee")]
        public decimal ProcessingFee { get; set; }

        [JsonPropertyName("total_cost")]
        public decimal TotalCost { get; set; }

        [JsonPropertyName("unit_cost")]
        public decimal UnitCost { get; set; }
        public decimal CurrentAmount => CurrentQty * UnitCost;

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;
        public string StatusDisplay => SelfUseSheetDisplay.InventoryStatus(Status);

        [JsonPropertyName("version")]
        public int Version { get; set; }

        [JsonPropertyName("completed_at")]
        public DateTime CompletedAt { get; set; }

        [JsonPropertyName("locations")]
        public List<SelfUseSheetInventoryLocationDto> Locations { get; set; } = new();

        [JsonPropertyName("source_lots")]
        public List<SelfUseSheetSourceLotDto> SourceLots { get; set; } = new();

        public string LocationSummary => Locations.Count == 0
            ? "위치 없음"
            : string.Join(", ", Locations.ConvertAll(x => $"{x.LocationName} {x.CurrentQty:N0}매"));
    }

    public class SelfUseSheetInventoryLocationDto
    {
        [JsonPropertyName("raw_material_location_id")]
        public long RawMaterialLocationId { get; set; }
        [JsonPropertyName("location_code")]
        public string LocationCode { get; set; } = string.Empty;
        [JsonPropertyName("location_name")]
        public string LocationName { get; set; } = string.Empty;
        [JsonPropertyName("location_type")]
        public string LocationType { get; set; } = string.Empty;
        [JsonPropertyName("current_qty")]
        public long CurrentQty { get; set; }
        public string DisplayText => $"{LocationName} / {CurrentQty:N0}매";
    }

    public class SelfUseSheetSourceLotDto
    {
        [JsonPropertyName("raw_material_inventory_lot_id")]
        public long? RawMaterialInventoryLotId { get; set; }
        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;
        [JsonPropertyName("source_location_name")]
        public string SourceLocationName { get; set; } = string.Empty;
        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;
        [JsonPropertyName("actual_consumed_qty")]
        public decimal ActualConsumedQty { get; set; }
    }

    public class SelfUseSheetInventorySummaryDto
    {
        [JsonPropertyName("lot_count")]
        public int LotCount { get; set; }

        [JsonPropertyName("initial_qty")]
        public long InitialQty { get; set; }

        [JsonPropertyName("used_qty")]
        public long UsedQty { get; set; }

        [JsonPropertyName("current_qty")]
        public long CurrentQty { get; set; }

        [JsonPropertyName("inventory_amount")]
        public decimal InventoryAmount { get; set; }
    }

    public class SelfUseSheetInventoryListDto
    {
        [JsonPropertyName("items")]
        public List<SelfUseSheetInventoryLotDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("summary")]
        public SelfUseSheetInventorySummaryDto Summary { get; set; } = new();
    }

    public class SelfUseSheetUseRequest
    {
        [JsonPropertyName("expected_version")]
        public int ExpectedVersion { get; set; }

        [JsonPropertyName("purpose_type")]
        public string PurposeType { get; set; } = string.Empty;

        [JsonPropertyName("qty")]
        public long Qty { get; set; }

        [JsonPropertyName("raw_material_location_id")]
        public long? RawMaterialLocationId { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class SelfUseSheetUseReverseRequest
    {
        [JsonPropertyName("expected_version")]
        public int ExpectedVersion { get; set; }

        [JsonPropertyName("reason")]
        public string Reason { get; set; } = string.Empty;
    }

    public class SelfUseSheetMovementDto
    {
        [JsonPropertyName("self_use_sheet_inventory_movement_id")]
        public long SelfUseSheetInventoryMovementId { get; set; }

        [JsonPropertyName("self_use_sheet_inventory_lot_id")]
        public long SelfUseSheetInventoryLotId { get; set; }

        [JsonPropertyName("inventory_lot_version")]
        public int InventoryLotVersion { get; set; }

        [JsonPropertyName("sheet_lot_no")]
        public string SheetLotNo { get; set; } = string.Empty;

        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("movement_type")]
        public string MovementType { get; set; } = string.Empty;
        public string MovementTypeDisplay => SelfUseSheetDisplay.Movement(MovementType);

        [JsonPropertyName("raw_material_location_id")]
        public long RawMaterialLocationId { get; set; }

        [JsonPropertyName("location_name")]
        public string LocationName { get; set; } = string.Empty;

        [JsonPropertyName("counterpart_location_name")]
        public string? CounterpartLocationName { get; set; }

        [JsonPropertyName("qty")]
        public long Qty { get; set; }

        [JsonPropertyName("balance_after")]
        public long BalanceAfter { get; set; }

        [JsonPropertyName("location_balance_after")]
        public long LocationBalanceAfter { get; set; }

        [JsonPropertyName("purpose_type")]
        public string? PurposeType { get; set; }
        public string PurposeDisplay => SelfUseSheetDisplay.Purpose(PurposeType);

        [JsonPropertyName("amount_snapshot")]
        public decimal AmountSnapshot { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("usage_product_display")]
        public string UsageProductDisplay { get; set; } = "-";

        [JsonPropertyName("usage_lot_display")]
        public string UsageLotDisplay { get; set; } = "-";

        [JsonPropertyName("usage_partner_display")]
        public string UsagePartnerDisplay { get; set; } = "-";

        [JsonPropertyName("work_instruction_no")]
        public string WorkInstructionNo { get; set; } = "-";

        [JsonPropertyName("work_group_seq")]
        public string WorkGroupSeq { get; set; } = "-";

        [JsonPropertyName("created_by")]
        public string CreatedBy { get; set; } = string.Empty;

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }

    public class SelfUseSheetMovementListDto
    {
        [JsonPropertyName("items")]
        public List<SelfUseSheetMovementDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }
    }

    public class SelfUseSheetTransferRequest
    {
        [JsonPropertyName("expected_version")]
        public int ExpectedVersion { get; set; }
        [JsonPropertyName("from_location_id")]
        public long FromLocationId { get; set; }
        [JsonPropertyName("to_location_id")]
        public long ToLocationId { get; set; }
        [JsonPropertyName("qty")]
        public long Qty { get; set; }
        [JsonPropertyName("reason")]
        public string Reason { get; set; } = string.Empty;
    }
}
