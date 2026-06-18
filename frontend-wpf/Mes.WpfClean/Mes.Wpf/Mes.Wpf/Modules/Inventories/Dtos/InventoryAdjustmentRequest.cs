using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Inventories.Dtos
{
    public class InventoryAdjustmentRequest
    {
        [JsonPropertyName("qty")]
        public int Qty { get; set; }

        [JsonPropertyName("stock_lot_no")]
        public string? StockLotNo { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}
