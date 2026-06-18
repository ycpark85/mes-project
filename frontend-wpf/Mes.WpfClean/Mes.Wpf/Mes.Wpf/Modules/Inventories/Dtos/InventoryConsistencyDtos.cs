using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Inventories.Dtos
{
    public class InventoryConsistencyListDto
    {
        [JsonPropertyName("items")]
        public List<InventoryConsistencyDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }
    }

    public class InventoryConsistencyDto
    {
        [JsonPropertyName("product_id")]
        public long ProductId { get; set; }

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("current_qty")]
        public int CurrentQty { get; set; }

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("movement_qty")]
        public int MovementQty { get; set; }

        [JsonPropertyName("diff_qty")]
        public int DiffQty { get; set; }
    }
}
