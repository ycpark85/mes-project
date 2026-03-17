using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Partners.Dtos
{
    public class PartnerListDto
    {
        [JsonPropertyName("items")]
        public List<PartnerDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }
    }
}