using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Inventories.Dtos
{
    public class InventoryMovementDto
    {
        [JsonPropertyName("inventory_movement_id")]
        public long InventoryMovementId { get; set; }

        [JsonPropertyName("product_id")]
        public long ProductId { get; set; }

        [JsonPropertyName("product_code")]
        public string? ProductCode { get; set; }

        [JsonPropertyName("product_name")]
        public string? ProductName { get; set; }

        [JsonPropertyName("movement_type")]
        public string MovementType { get; set; } = string.Empty;

        [JsonPropertyName("qty")]
        public int Qty { get; set; }

        [JsonPropertyName("balance_after")]
        public int BalanceAfter { get; set; }

        [JsonPropertyName("source_type")]
        public string? SourceType { get; set; }

        [JsonPropertyName("source_id")]
        public long? SourceId { get; set; }

        [JsonPropertyName("order_line_id")]
        public long? OrderLineId { get; set; }

        [JsonPropertyName("inspection_schedule_id")]
        public long? InspectionScheduleId { get; set; }

        [JsonPropertyName("inspection_result_id")]
        public long? InspectionResultId { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }
}