using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.InspectionSchedules.Dtos
{
    public class InspectionScheduleUpdateRequest
    {
        [JsonPropertyName("inspection_date")]
        public DateTime? InspectionDate { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }
}