using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Products.Dtos
{
    public class ProductBulkCreateRequest
    {
        [JsonPropertyName("items")]
        public List<ProductBulkItemRequest> Items { get; set; } = new();
    }

    public class ProductBulkItemRequest
    {
        [JsonPropertyName("row_number")]
        public int RowNumber { get; set; }

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = string.Empty;

        [JsonPropertyName("drawing_no")]
        public string DrawingNo { get; set; } = string.Empty;

        [JsonPropertyName("template_code")]
        public string TemplateCode { get; set; } = string.Empty;

        [JsonPropertyName("panel_width_mm")]
        public int? PanelWidthMm { get; set; }

        [JsonPropertyName("panel_length_mm")]
        public int? PanelLengthMm { get; set; }

        [JsonPropertyName("product_spec")]
        public string? ProductSpec { get; set; }

        [JsonPropertyName("cut_qty_per_panel")]
        public int? CutQtyPerPanel { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}