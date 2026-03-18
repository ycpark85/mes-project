using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingCreateRequest
    {
        [JsonPropertyName("drawing_no")]
        public string DrawingNo { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;
    }
}