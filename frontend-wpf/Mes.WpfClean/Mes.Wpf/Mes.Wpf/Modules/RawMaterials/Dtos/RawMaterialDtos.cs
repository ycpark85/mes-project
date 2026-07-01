using Mes.Wpf.Core.Common;
using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.RawMaterials.Dtos
{
    public class RawMaterialDto
    {
        [JsonPropertyName("raw_material_id")]
        public long RawMaterialId { get; set; }

        [JsonPropertyName("material_code")]
        public string MaterialCode { get; set; } = string.Empty;

        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("material_spec")]
        public string? MaterialSpec { get; set; }

        [JsonPropertyName("width_mm")]
        public int? WidthMm { get; set; }

        [JsonPropertyName("material_type")]
        public string? MaterialType { get; set; }

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = "M";

        [JsonPropertyName("standard_unit_cost")]
        public decimal? StandardUnitCost { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("current_qty")]
        public decimal CurrentQty { get; set; }
    }

    public class RawMaterialListDto
    {
        [JsonPropertyName("items")]
        public List<RawMaterialDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }
    }

    public class RawMaterialCreateRequest
    {
        [JsonPropertyName("material_code")]
        public string MaterialCode { get; set; } = string.Empty;

        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("material_spec")]
        public string? MaterialSpec { get; set; }

        [JsonPropertyName("width_mm")]
        public int? WidthMm { get; set; }

        [JsonPropertyName("material_type")]
        public string? MaterialType { get; set; }

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = "M";

        [JsonPropertyName("standard_unit_cost")]
        public decimal? StandardUnitCost { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialUpdateRequest
    {
        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("material_spec")]
        public string? MaterialSpec { get; set; }

        [JsonPropertyName("width_mm")]
        public int? WidthMm { get; set; }

        [JsonPropertyName("material_type")]
        public string? MaterialType { get; set; }

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = "M";

        [JsonPropertyName("standard_unit_cost")]
        public decimal? StandardUnitCost { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialLocationDto
    {
        [JsonPropertyName("raw_material_location_id")]
        public long RawMaterialLocationId { get; set; }

        [JsonPropertyName("location_code")]
        public string LocationCode { get; set; } = string.Empty;

        [JsonPropertyName("location_name")]
        public string LocationName { get; set; } = string.Empty;

        [JsonPropertyName("location_type")]
        public string LocationType { get; set; } = "INTERNAL_WAREHOUSE";

        [JsonPropertyName("partner_id")]
        public long? PartnerId { get; set; }

        [JsonPropertyName("partner_name")]
        public string? PartnerName { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("current_qty")]
        public decimal CurrentQty { get; set; }
    }

    public class RawMaterialLocationListDto
    {
        [JsonPropertyName("items")]
        public List<RawMaterialLocationDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }
    }

    public class RawMaterialLocationCreateRequest
    {
        [JsonPropertyName("location_code")]
        public string? LocationCode { get; set; }

        [JsonPropertyName("location_name")]
        public string LocationName { get; set; } = string.Empty;

        [JsonPropertyName("location_type")]
        public string LocationType { get; set; } = "INTERNAL_WAREHOUSE";

        [JsonPropertyName("partner_id")]
        public long? PartnerId { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialLocationUpdateRequest
    {
        [JsonPropertyName("location_name")]
        public string LocationName { get; set; } = string.Empty;

        [JsonPropertyName("location_type")]
        public string LocationType { get; set; } = "INTERNAL_WAREHOUSE";

        [JsonPropertyName("partner_id")]
        public long? PartnerId { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialInventoryLotDto
    {
        [JsonPropertyName("raw_material_inventory_lot_id")]
        public long RawMaterialInventoryLotId { get; set; }

        [JsonPropertyName("raw_material_id")]
        public long RawMaterialId { get; set; }

        [JsonPropertyName("raw_material_location_id")]
        public long RawMaterialLocationId { get; set; }

        [JsonPropertyName("material_code")]
        public string MaterialCode { get; set; } = string.Empty;

        [JsonPropertyName("material_name")]
        public string MaterialName { get; set; } = string.Empty;

        [JsonPropertyName("location_name")]
        public string LocationName { get; set; } = string.Empty;

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("current_qty")]
        public decimal CurrentQty { get; set; }

        [JsonPropertyName("unit_cost")]
        public decimal? UnitCost { get; set; }

        [JsonPropertyName("inventory_amount")]
        public decimal? InventoryAmount { get; set; }
    }

    public class RawMaterialInventoryLotListDto
    {
        [JsonPropertyName("items")]
        public List<RawMaterialInventoryLotDto> Items { get; set; } = new();
    }

    public class RawMaterialMovementDto
    {
        [JsonPropertyName("raw_material_inventory_movement_id")]
        public long RawMaterialInventoryMovementId { get; set; }

        [JsonPropertyName("material_code")]
        public string? MaterialCode { get; set; }

        [JsonPropertyName("material_name")]
        public string? MaterialName { get; set; }

        [JsonPropertyName("location_name")]
        public string? LocationName { get; set; }

        [JsonPropertyName("lot_no")]
        public string? LotNo { get; set; }

        [JsonPropertyName("movement_type")]
        public string MovementType { get; set; } = string.Empty;

        public string MovementTypeDisplay => MovementType switch
        {
            "INBOUND" => "\uC785\uACE0",
            "TRANSFER_OUT" => "\uC774\uB3D9\uCD9C\uACE0",
            "TRANSFER_IN" => "\uC774\uB3D9\uC785\uACE0",
            "ADJUST_IN" => "\uC7AC\uACE0\uC99D\uAC00",
            "ADJUST_OUT" => "\uC7AC\uACE0\uAC10\uC18C",
            "CONSUME_OUT" => "\uC0AC\uC6A9\uCC28\uAC10",
            "CONSUME_REVERSE" => "\uC0AC\uC6A9\uCDE8\uC18C",
            _ => MovementType
        };

        [JsonPropertyName("qty")]
        public decimal Qty { get; set; }

        [JsonPropertyName("balance_after")]
        public decimal BalanceAfter { get; set; }

        [JsonPropertyName("amount_snapshot")]
        public decimal? AmountSnapshot { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }

    public class RawMaterialMovementListDto
    {
        [JsonPropertyName("items")]
        public List<RawMaterialMovementDto> Items { get; set; } = new();
    }

    public class RawMaterialInboundRequest
    {
        [JsonPropertyName("raw_material_id")]
        public long RawMaterialId { get; set; }

        [JsonPropertyName("raw_material_location_id")]
        public long RawMaterialLocationId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("qty")]
        public decimal Qty { get; set; }

        [JsonPropertyName("unit_cost")]
        public decimal? UnitCost { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialTransferRequest
    {
        [JsonPropertyName("raw_material_inventory_lot_id")]
        public long RawMaterialInventoryLotId { get; set; }

        [JsonPropertyName("to_location_id")]
        public long ToLocationId { get; set; }

        [JsonPropertyName("qty")]
        public decimal Qty { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialAdjustmentRequest
    {
        [JsonPropertyName("raw_material_inventory_lot_id")]
        public long RawMaterialInventoryLotId { get; set; }

        [JsonPropertyName("qty")]
        public decimal Qty { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class RawMaterialEditModel : ViewModelBase
    {
        private long? _rawMaterialId;
        private string _materialCode = string.Empty;
        private string _materialName = string.Empty;
        private string? _materialSpec;
        private int? _widthMm;
        private string? _materialType;
        private string _uom = "M";
        private decimal? _standardUnitCost;
        private bool _isActive = true;
        private string? _memo;

        public long? RawMaterialId { get => _rawMaterialId; set => SetProperty(ref _rawMaterialId, value); }
        public string MaterialCode { get => _materialCode; set => SetProperty(ref _materialCode, value); }
        public string MaterialName { get => _materialName; set => SetProperty(ref _materialName, value); }
        public string? MaterialSpec { get => _materialSpec; set => SetProperty(ref _materialSpec, value); }
        public int? WidthMm { get => _widthMm; set => SetProperty(ref _widthMm, value); }
        public string? MaterialType { get => _materialType; set => SetProperty(ref _materialType, value); }
        public string Uom { get => _uom; set => SetProperty(ref _uom, value); }
        public decimal? StandardUnitCost { get => _standardUnitCost; set => SetProperty(ref _standardUnitCost, value); }
        public bool IsActive { get => _isActive; set => SetProperty(ref _isActive, value); }
        public string? Memo { get => _memo; set => SetProperty(ref _memo, value); }

        public void LoadFromDto(RawMaterialDto dto)
        {
            RawMaterialId = dto.RawMaterialId;
            MaterialCode = dto.MaterialCode;
            MaterialName = dto.MaterialName;
            MaterialSpec = dto.MaterialSpec;
            WidthMm = dto.WidthMm;
            MaterialType = dto.MaterialType;
            Uom = dto.Uom;
            StandardUnitCost = dto.StandardUnitCost;
            IsActive = dto.IsActive;
            Memo = dto.Memo;
        }

        public void Clear()
        {
            RawMaterialId = null;
            MaterialCode = string.Empty;
            MaterialName = string.Empty;
            MaterialSpec = null;
            WidthMm = null;
            MaterialType = null;
            Uom = "M";
            StandardUnitCost = null;
            IsActive = true;
            Memo = null;
        }
    }

    public class RawMaterialLocationEditModel : ViewModelBase
    {
        private long? _rawMaterialLocationId;
        private string _locationCode = string.Empty;
        private string _locationName = string.Empty;
        private string _locationType = "INTERNAL_WAREHOUSE";
        private long? _partnerId;
        private string _partnerName = string.Empty;
        private bool _isActive = true;
        private string? _memo;

        public long? RawMaterialLocationId { get => _rawMaterialLocationId; set => SetProperty(ref _rawMaterialLocationId, value); }
        public string LocationCode
        {
            get => _locationCode;
            set
            {
                if (SetProperty(ref _locationCode, value))
                {
                    OnPropertyChanged(nameof(LocationCodeDisplay));
                }
            }
        }

        public string LocationCodeDisplay => string.IsNullOrWhiteSpace(LocationCode) ? "저장 시 자동 생성" : LocationCode;
        public string LocationName { get => _locationName; set => SetProperty(ref _locationName, value); }
        public string LocationType { get => _locationType; set => SetProperty(ref _locationType, value); }
        public long? PartnerId { get => _partnerId; set => SetProperty(ref _partnerId, value); }
        public string PartnerName
        {
            get => _partnerName;
            set
            {
                if (SetProperty(ref _partnerName, value))
                {
                    PartnerId = null;
                }
            }
        }
        public bool IsActive { get => _isActive; set => SetProperty(ref _isActive, value); }
        public string? Memo { get => _memo; set => SetProperty(ref _memo, value); }

        public void ApplyPartner(long partnerId, string partnerName)
        {
            PartnerName = partnerName;
            PartnerId = partnerId;
            LocationName = partnerName;
        }

        public void LoadFromDto(RawMaterialLocationDto dto)
        {
            RawMaterialLocationId = dto.RawMaterialLocationId;
            LocationCode = dto.LocationCode;
            LocationName = dto.LocationName;
            LocationType = dto.LocationType;
            PartnerName = dto.PartnerName ?? string.Empty;
            PartnerId = dto.PartnerId;
            IsActive = dto.IsActive;
            Memo = dto.Memo;
        }

        public void Clear()
        {
            RawMaterialLocationId = null;
            LocationCode = string.Empty;
            LocationName = string.Empty;
            LocationType = "INTERNAL_WAREHOUSE";
            PartnerName = string.Empty;
            PartnerId = null;
            IsActive = true;
            Memo = null;
        }
    }
}
