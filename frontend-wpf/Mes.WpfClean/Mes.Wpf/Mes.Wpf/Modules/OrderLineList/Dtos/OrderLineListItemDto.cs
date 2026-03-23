using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLineList.Dtos
{
    public class OrderLineListItemDto
    {
        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("order_no")]
        public string OrderNo { get; set; } = string.Empty;

        [JsonPropertyName("line_no")]
        public int LineNo { get; set; }

        [JsonPropertyName("partner_id")]
        public long PartnerId { get; set; }

        [JsonPropertyName("product_id")]
        public long ProductId { get; set; }

        [JsonPropertyName("order_date")]
        public DateTime OrderDate { get; set; }

        [JsonPropertyName("due_date")]
        public DateTime DueDate { get; set; }

        [JsonPropertyName("order_qty")]
        public int OrderQty { get; set; }

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = string.Empty;

        [JsonPropertyName("customer_po")]
        public string? CustomerPo { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("priority")]
        public int Priority { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("product_code")]
        public string? ProductCode { get; set; }

        [JsonPropertyName("product_name")]
        public string? ProductName { get; set; }

        [JsonPropertyName("has_lot")]
        public bool HasLot { get; set; }

        [JsonPropertyName("lot_count")]
        public int LotCount { get; set; }

        public string StatusDisplay => Status == "CLOSED" ? "IN_PROGRESS" : Status;
    }
}