using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingRevisionCreateRequest
    {
        [JsonPropertyName("rev_no")]
        public string RevNo { get; set; } = string.Empty;

        [JsonPropertyName("set_as_current")]
        public bool SetAsCurrent { get; set; } = true;
    }
}