using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.RoutingTemplates.Dtos
{
    public class RoutingTemplateStepCreateRequest
    {
        [JsonPropertyName("step_seq")]
        public int StepSeq { get; set; }

        [JsonPropertyName("process_id")]
        public long ProcessId { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }
    }
}