using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Core.Models
{
    public class PagedResult<T>
    {
        [JsonPropertyName("items")]
        public List<T> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }
    }
}