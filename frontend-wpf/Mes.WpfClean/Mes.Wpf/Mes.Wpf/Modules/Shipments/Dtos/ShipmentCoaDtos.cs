using Mes.Wpf.Core.Common;
using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Shipments.Dtos
{
    public class ShipmentCoaDto
    {
        [JsonPropertyName("shipment_coa_id")]
        public long ShipmentCoaId { get; set; }

        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("product_id")]
        public long ProductId { get; set; }

        [JsonPropertyName("product_name_snapshot")]
        public string ProductNameSnapshot { get; set; } = string.Empty;

        [JsonPropertyName("product_spec_snapshot")]
        public string ProductSpecSnapshot { get; set; } = string.Empty;

        [JsonPropertyName("material_snapshot")]
        public string MaterialSnapshot { get; set; } = string.Empty;

        [JsonPropertyName("partner_name_snapshot")]
        public string PartnerNameSnapshot { get; set; } = string.Empty;

        [JsonPropertyName("lot_nos_snapshot")]
        public string LotNosSnapshot { get; set; } = string.Empty;

        [JsonPropertyName("stock_lot_nos_snapshot")]
        public string? StockLotNosSnapshot { get; set; }

        [JsonPropertyName("production_lot_nos_snapshot")]
        public string? ProductionLotNosSnapshot { get; set; }

        [JsonPropertyName("quantity_snapshot")]
        public int QuantitySnapshot { get; set; }

        [JsonPropertyName("inspection_date_snapshot")]
        public DateTime InspectionDateSnapshot { get; set; }

        [JsonPropertyName("is_printed_product_snapshot")]
        public bool IsPrintedProductSnapshot { get; set; }

        [JsonPropertyName("issued_at")]
        public DateTime IssuedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime UpdatedAt { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class ShipmentCoaUpdateRequest
    {
        [JsonPropertyName("quantity_snapshot")]
        public int QuantitySnapshot { get; set; }

        [JsonPropertyName("inspection_date_snapshot")]
        public string InspectionDateSnapshot { get; set; } = string.Empty;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class ShipmentCoaEditModel : ViewModelBase
    {
        private int _quantitySnapshot;
        private DateTime? _inspectionDateSnapshot;
        private string _memo = string.Empty;

        public int QuantitySnapshot
        {
            get => _quantitySnapshot;
            set => SetProperty(ref _quantitySnapshot, value);
        }

        public DateTime? InspectionDateSnapshot
        {
            get => _inspectionDateSnapshot;
            set => SetProperty(ref _inspectionDateSnapshot, value);
        }

        public string Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public void LoadFromDto(ShipmentCoaDto dto)
        {
            QuantitySnapshot = dto.QuantitySnapshot;
            InspectionDateSnapshot = dto.InspectionDateSnapshot;
            Memo = dto.Memo ?? string.Empty;
        }

        public void Clear()
        {
            QuantitySnapshot = 0;
            InspectionDateSnapshot = null;
            Memo = string.Empty;
        }
    }
}