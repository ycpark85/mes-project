using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.InspectionSchedules.Dtos
{
    public class InspectionScheduleCreateRequest
    {
        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("inspection_date")]
        public DateTime InspectionDate { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}