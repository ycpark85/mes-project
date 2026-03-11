using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.DefectTypes.Dtos
{
    public class DefectTypeDto
    {
        [JsonPropertyName("defect_type_id")]
        public long DefectTypeId { get; set; }

        [JsonPropertyName("code")]
        public string DefectCode { get; set; } = string.Empty;

        [JsonPropertyName("name")]
        public string DefectName { get; set; } = string.Empty;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }
    }
}