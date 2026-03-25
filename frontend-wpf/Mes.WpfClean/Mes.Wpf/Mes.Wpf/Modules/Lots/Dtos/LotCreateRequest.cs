using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Lots.Dtos
{
    public class LotCreateRequest
    {
        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("parent_lot_id")]
        public long? ParentLotId { get; set; }

        [JsonPropertyName("lot_qty")]
        public int LotQty { get; set; }

        [JsonPropertyName("created_date")]
        public DateTime? CreatedDate { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("material_lot_no")]
        public string? MaterialLotNo { get; set; }

        [JsonPropertyName("material_used_qty")]
        public decimal? MaterialUsedQty { get; set; }

        [JsonPropertyName("material_sheet_count")]
        public int? MaterialSheetCount { get; set; }
    }
}