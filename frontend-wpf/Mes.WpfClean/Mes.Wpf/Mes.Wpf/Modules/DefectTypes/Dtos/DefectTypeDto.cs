using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.DefectTypes.Dtos
{
    public class DefectTypeDto
    {
        [JsonPropertyName("defect_type_id")]
        public long DefectTypeId { get; set; }

        [JsonPropertyName("code")]
        public string DefectCode { get; set; } = string.Empty;

        [JsonPropertyName("category1_name")]
        public string Category1Name { get; set; } = string.Empty;

        [JsonPropertyName("category2_name")]
        public string Category2Name { get; set; } = string.Empty;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }
    }
}