using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLineList.Dtos
{
    public class OrderLineDetailUpdateRequest
    {
        [JsonPropertyName("due_date")]
        public DateTime DueDate { get; set; }

        [JsonPropertyName("order_qty")]
        public int OrderQty { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}