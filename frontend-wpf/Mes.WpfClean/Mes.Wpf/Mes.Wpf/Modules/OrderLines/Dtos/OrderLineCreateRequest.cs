using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLines.Dtos
{
    public class OrderLineCreateRequest
    {
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
    }
}