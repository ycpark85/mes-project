using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.OrderLineList.Dtos
{
    public class OrderLineShortCloseRequest
    {
        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}