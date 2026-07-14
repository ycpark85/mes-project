using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;
using Mes.Vendor.Wpf.Core;

namespace Mes.Vendor.Wpf.Dtos;

public sealed class BohyunOutsourceListDto
{
    [JsonPropertyName("items")]
    public List<BohyunOutsourceListItemDto> Items { get; set; } = new();

    [JsonPropertyName("total_count")]
    public int TotalCount { get; set; }

    [JsonPropertyName("page")]
    public int Page { get; set; }

    [JsonPropertyName("size")]
    public int Size { get; set; }

    [JsonPropertyName("processing_fee_total")]
    public decimal ProcessingFeeTotal { get; set; }
}

public sealed class BohyunOutsourceListItemDto
{
    [JsonPropertyName("outsource_work_group_id")]
    public long OutsourceWorkGroupId { get; set; }

    [JsonPropertyName("outsource_work_instruction_id")]
    public long OutsourceWorkInstructionId { get; set; }

    [JsonPropertyName("representative_product_name")]
    public string? RepresentativeProductName { get; set; }

    [JsonPropertyName("instruction_no")]
    public string InstructionNo { get; set; } = string.Empty;

    [JsonPropertyName("instruction_date")]
    public DateTime? InstructionDate { get; set; }

    [JsonPropertyName("process_type")]
    public string ProcessType { get; set; } = string.Empty;

    [JsonPropertyName("partner_name")]
    public string PartnerName { get; set; } = string.Empty;

    [JsonPropertyName("inbound_source_name")]
    public string InboundSourceName { get; set; } = string.Empty;

    [JsonPropertyName("is_bundle")]
    public bool IsBundle { get; set; }

    [JsonPropertyName("group_seq")]
    public string? GroupSeq { get; set; }

    [JsonPropertyName("sheet_qty")]
    public int SheetQty { get; set; }

    [JsonPropertyName("work_done_sheet_qty")]
    public int? WorkDoneSheetQty { get; set; }

    [JsonPropertyName("sheet_cut_count")]
    public int SheetCutCount { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("vendor_received_at")]
    public DateTime? VendorReceivedAt { get; set; }

    [JsonPropertyName("work_done_at")]
    public DateTime? WorkDoneAt { get; set; }

    [JsonPropertyName("shipped_at")]
    public DateTime? ShippedAt { get; set; }

    [JsonPropertyName("outsource_processing_fee")]
    public decimal? OutsourceProcessingFee { get; set; }

    [JsonPropertyName("work_done_remark")]
    public string WorkDoneRemark { get; set; } = string.Empty;

    [JsonPropertyName("lot_nos")]
    public List<string> LotNos { get; set; } = new();

    [JsonPropertyName("product_names")]
    public List<string> ProductNames { get; set; } = new();

    [JsonPropertyName("items")]
    public List<BohyunOutsourceGroupItemDto> Items { get; set; } = new();
}

public sealed class BohyunOutsourceGroupItemDto
{
    [JsonPropertyName("lot_no")]
    public string LotNo { get; set; } = string.Empty;

    [JsonPropertyName("order_no")]
    public string OrderNo { get; set; } = string.Empty;

    [JsonPropertyName("line_no")]
    public int? LineNo { get; set; }

    [JsonPropertyName("product_code")]
    public string ProductCode { get; set; } = string.Empty;

    [JsonPropertyName("product_name")]
    public string ProductName { get; set; } = string.Empty;

    [JsonPropertyName("cuts_per_sheet")]
    public int CutsPerSheet { get; set; }

    [JsonPropertyName("expected_output_qty")]
    public int? ExpectedOutputQty { get; set; }

    [JsonPropertyName("actual_output_qty")]
    public int? ActualOutputQty { get; set; }
}

public sealed class BohyunWorkDoneRequest
{
    [JsonPropertyName("work_done_sheet_qty")]
    public int WorkDoneSheetQty { get; set; }

    [JsonPropertyName("outsource_processing_fee")]
    public decimal? OutsourceProcessingFee { get; set; }

    [JsonPropertyName("remark")]
    public string? Remark { get; set; }
}

public sealed class BohyunShipBatchRequest
{
    [JsonPropertyName("group_ids")]
    public List<long> GroupIds { get; set; } = new();
}

public sealed class BohyunOutsourceRow : BindableBase
{
    private bool _isChecked;

    public bool IsChecked
    {
        get => _isChecked;
        set => SetProperty(ref _isChecked, value);
    }

    public long OutsourceWorkGroupId { get; init; }
    public string InstructionNo { get; init; } = string.Empty;
    public DateTime? InstructionDate { get; init; }
    public string ProcessType { get; init; } = string.Empty;
    public string PartnerName { get; init; } = string.Empty;
    public string InboundSourceName { get; init; } = string.Empty;
    public bool IsBundle { get; init; }
    public int SheetQty { get; init; }
    public int? WorkDoneSheetQty { get; init; }
    public int SheetCutCount { get; init; }
    public string Status { get; init; } = string.Empty;
    public DateTime? VendorReceivedAt { get; init; }
    public DateTime? WorkDoneAt { get; init; }
    public DateTime? ShippedAt { get; init; }
    public decimal? OutsourceProcessingFee { get; init; }
    public string WorkDoneRemark { get; init; } = string.Empty;
    public List<string> LotNos { get; init; } = new();
    public List<string> ProductNames { get; init; } = new();
    public List<BohyunOutsourceGroupItemDto> Items { get; init; } = new();

    public string StatusName => Status switch
    {
        "WAITING_INBOUND" => "입고대기",
        "INBOUNDED" => "입고완료",
        "WORK_DONE" => "작업완료",
        "SHIPPED" => "출고완료",
        _ => Status
    };

    public string ProcessTypeName => ProcessType switch
    {
        "CUT" => "재단",
        "PRINT" => "인쇄",
        "DIECUT" => "도무송",
        _ => ProcessType
    };

    public string WorkTypeName => IsBundle ? "묶음" : "개별";
    public string LotNosText => LotNos.Count == 0 ? string.Empty : string.Join(", ", LotNos);
    public string ProductNamesText => ProductNames.Count == 0 ? string.Empty : string.Join(", ", ProductNames.Distinct());
    public bool CanInbound => Status == "WAITING_INBOUND";
    public bool CanWorkDone => Status == "INBOUNDED";
    public bool CanShip => Status == "WORK_DONE";

    public static BohyunOutsourceRow FromDto(BohyunOutsourceListItemDto dto)
    {
        return new BohyunOutsourceRow
        {
            OutsourceWorkGroupId = dto.OutsourceWorkGroupId,
            InstructionNo = dto.InstructionNo,
            InstructionDate = dto.InstructionDate,
            ProcessType = dto.ProcessType,
            PartnerName = dto.PartnerName,
            InboundSourceName = dto.InboundSourceName,
            IsBundle = dto.IsBundle,
            SheetQty = dto.SheetQty,
            WorkDoneSheetQty = dto.WorkDoneSheetQty,
            SheetCutCount = dto.SheetCutCount,
            Status = dto.Status,
            VendorReceivedAt = dto.VendorReceivedAt,
            WorkDoneAt = dto.WorkDoneAt,
            ShippedAt = dto.ShippedAt,
            OutsourceProcessingFee = dto.OutsourceProcessingFee,
            WorkDoneRemark = dto.WorkDoneRemark,
            LotNos = dto.LotNos ?? new List<string>(),
            ProductNames = dto.ProductNames ?? new List<string>(),
            Items = dto.Items ?? new List<BohyunOutsourceGroupItemDto>()
        };
    }
}
