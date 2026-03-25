using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Lots.Dtos
{
    public class LotListResponse
    {
        [JsonPropertyName("items")]
        public List<LotDto> Items { get; set; } = new();

        [JsonPropertyName("meta")]
        public LotListMetaDto Meta { get; set; } = new();
    }

    public class LotListMetaDto
    {
        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }

        [JsonPropertyName("total")]
        public int Total { get; set; }
    }
}