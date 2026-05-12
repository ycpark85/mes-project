using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.DefectTypes.Dtos
{
    public class DefectTypeCreateRequest
    {
        [JsonPropertyName("code")]
        public string Code { get; set; } = string.Empty;

        [JsonPropertyName("category1_name")]
        public string Category1Name { get; set; } = string.Empty;

        [JsonPropertyName("category2_name")]
        public string Category2Name { get; set; } = string.Empty;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;
    }
}