using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Partners.Dtos
{
    public class PartnerCreateRequest
    {
        [JsonPropertyName("partner_type")]
        public string PartnerType { get; set; } = "CUSTOMER";

        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("business_no")]
        public string? BusinessNo { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;
    }
}