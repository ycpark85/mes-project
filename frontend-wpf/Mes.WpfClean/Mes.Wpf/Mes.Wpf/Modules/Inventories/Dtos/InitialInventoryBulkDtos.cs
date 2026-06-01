using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Inventories.Dtos
{
    public class InitialInventoryBulkRequest
    {
        [JsonPropertyName("items")]
        public List<InitialInventoryBulkItemRequest> Items { get; set; } = new();
    }

    public class InitialInventoryBulkItemRequest
    {
        [JsonPropertyName("row_number")]
        public int RowNumber { get; set; }

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("initial_qty")]
        public int InitialQty { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class InitialInventoryBulkResultDto
    {
        [JsonPropertyName("total_count")]
        public int TotalCount { get; set; }

        [JsonPropertyName("success_count")]
        public int SuccessCount { get; set; }

        [JsonPropertyName("skipped_count")]
        public int SkippedCount { get; set; }

        [JsonPropertyName("failure_count")]
        public int FailureCount { get; set; }

        [JsonPropertyName("errors")]
        public List<InitialInventoryBulkErrorDto> Errors { get; set; } = new();
    }

    public class InitialInventoryBulkErrorDto
    {
        [JsonPropertyName("row_number")]
        public int RowNumber { get; set; }

        [JsonPropertyName("product_code")]
        public string? ProductCode { get; set; }

        [JsonPropertyName("lot_no")]
        public string? LotNo { get; set; }

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }
}
