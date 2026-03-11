using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.DefectTypes.Dtos
{
    public class DefectTypeListDto
    {
        [JsonPropertyName("items")]
        public List<DefectTypeDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }
    }
}