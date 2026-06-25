using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.InspectionSchedules.Dtos
{
    public class InspectionResultManagementItemDto
    {
        public int RowNo { get; set; }

        [JsonPropertyName("inspection_result_id")]
        public long InspectionResultId { get; set; }

        [JsonPropertyName("inspection_schedule_id")]
        public long InspectionScheduleId { get; set; }

        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("inspection_date")]
        public DateTime InspectionDate { get; set; }

        [JsonPropertyName("due_date")]
        public DateTime DueDate { get; set; }

        [JsonPropertyName("partner_name")]
        public string PartnerName { get; set; } = string.Empty;

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("order_qty")]
        public int OrderQty { get; set; }

        [JsonPropertyName("good_qty")]
        public int GoodQty { get; set; }

        [JsonPropertyName("uninspected_qty")]
        public int UninspectedQty { get; set; }

        [JsonPropertyName("received_qty")]
        public int ReceivedQty { get; set; }

        [JsonPropertyName("result_ship_qty")]
        public int ResultShipQty { get; set; }

        [JsonPropertyName("discard_qty")]
        public int DiscardQty { get; set; }

        public int TotalDisposalQty => DiscardQty + UninspectedQty;

        [JsonPropertyName("stock_in_qty")]
        public int StockInQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("created_by")]
        public string? CreatedBy { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime UpdatedAt { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}
