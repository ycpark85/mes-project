using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.DefectTypes.Dtos
{
    public class DefectTypeUpdateRequest
    {
        [JsonPropertyName("category1_name")]
        public string? Category1Name { get; set; }

        [JsonPropertyName("category2_name")]
        public string? Category2Name { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("is_active")]
        public bool? IsActive { get; set; }
    }
}