using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Products.Dtos
{
    public class ProductBulkResultDto
    {
        [JsonPropertyName("total_count")]
        public int TotalCount { get; set; }

        [JsonPropertyName("success_count")]
        public int SuccessCount { get; set; }

        [JsonPropertyName("failure_count")]
        public int FailureCount { get; set; }

        [JsonPropertyName("created_items")]
        public List<ProductDto> CreatedItems { get; set; } = new();

        [JsonPropertyName("errors")]
        public List<ProductBulkErrorDto> Errors { get; set; } = new();
    }

    public class ProductBulkErrorDto
    {
        [JsonPropertyName("row_number")]
        public int RowNumber { get; set; }

        [JsonPropertyName("field")]
        public string Field { get; set; } = string.Empty;

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }
}