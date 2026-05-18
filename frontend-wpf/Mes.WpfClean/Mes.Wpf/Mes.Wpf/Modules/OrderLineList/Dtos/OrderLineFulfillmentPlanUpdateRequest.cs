using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLineList.Dtos
{
    public class OrderLineFulfillmentPlanUpdateRequest
    {
        [JsonPropertyName("fulfillment_mode")]
        public string FulfillmentMode { get; set; } = string.Empty;

        [JsonPropertyName("production_policy")]
        public string ProductionPolicy { get; set; } = string.Empty;

        [JsonPropertyName("extra_production_qty")]
        public int ExtraProductionQty { get; set; }
    }
}