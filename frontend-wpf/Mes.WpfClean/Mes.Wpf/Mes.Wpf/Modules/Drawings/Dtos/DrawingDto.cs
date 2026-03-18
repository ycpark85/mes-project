using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingDto
    {
        [JsonPropertyName("drawing_id")]
        public long DrawingId { get; set; }

        [JsonPropertyName("drawing_no")]
        public string DrawingNo { get; set; } = string.Empty;

        [JsonPropertyName("current_revision_id")]
        public long? CurrentRevisionId { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }
    }
}