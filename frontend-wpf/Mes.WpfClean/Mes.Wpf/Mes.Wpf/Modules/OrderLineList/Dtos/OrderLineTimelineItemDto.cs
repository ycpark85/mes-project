using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLineList.Dtos
{
    public class OrderLineTimelineItemDto
    {
        [JsonPropertyName("event_type")]
        public string EventType { get; set; } = string.Empty;

        [JsonPropertyName("event_label")]
        public string EventLabel { get; set; } = string.Empty;

        [JsonPropertyName("event_at")]
        public DateTime EventAt { get; set; }

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;

        [JsonPropertyName("ref_type")]
        public string? RefType { get; set; }

        [JsonPropertyName("ref_id")]
        public long? RefId { get; set; }
    }
}