using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.BohyunOutsourceManagement.Dtos
{
    public class BohyunOutsourceShipRequest
    {
        [JsonPropertyName("group_ids")]
        public List<long> GroupIds { get; set; } = new();
    }
}