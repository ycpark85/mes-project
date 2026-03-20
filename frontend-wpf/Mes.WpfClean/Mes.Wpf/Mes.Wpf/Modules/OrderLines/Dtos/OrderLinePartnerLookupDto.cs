using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLines.Dtos
{
    public class OrderLinePartnerLookupDto
    {
        [JsonPropertyName("partner_id")]
        public long PartnerId { get; set; }

        [JsonPropertyName("partner_type")]
        public string PartnerType { get; set; } = string.Empty;

        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("business_no")]
        public string? BusinessNo { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        public string DisplayName => $"{Name}";
    }
}