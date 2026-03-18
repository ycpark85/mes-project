using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingUpdateRequest
    {
        [JsonPropertyName("drawing_no")]
        public string? DrawingNo { get; set; }

        [JsonPropertyName("is_active")]
        public bool? IsActive { get; set; }
    }
}