using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Partners.Dtos
{
    public class PartnerBulkCreateRequest
    {
        [JsonPropertyName("items")]
        public List<PartnerBulkItemRequest> Items { get; set; } = new();
    }

    public class PartnerBulkItemRequest
    {
        [JsonPropertyName("row_number")]
        public int RowNumber { get; set; }

        [JsonPropertyName("partner_type")]
        public string PartnerType { get; set; } = string.Empty;

        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("business_no")]
        public string BusinessNo { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;
    }
}