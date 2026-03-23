using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLineList.Dtos
{
    public class OrderLineDetailLotDto
    {
        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("lot_type")]
        public string LotType { get; set; } = string.Empty;

        [JsonPropertyName("parent_lot_id")]
        public long? ParentLotId { get; set; }

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("current_process_name")]
        public string? CurrentProcessName { get; set; }

        [JsonPropertyName("is_editable")]
        public bool IsEditable { get; set; }

        [JsonPropertyName("can_cancel")]
        public bool CanCancel { get; set; }

        [JsonPropertyName("can_create_rework")]
        public bool CanCreateRework { get; set; }

        public string StatusDisplay => Status == "CLOSED" ? "IN_PROGRESS" : Status;
    }
}