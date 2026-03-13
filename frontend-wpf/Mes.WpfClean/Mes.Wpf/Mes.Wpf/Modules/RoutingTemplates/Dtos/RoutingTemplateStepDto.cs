using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.RoutingTemplates.Dtos
{
    public class RoutingTemplateStepDto
    {
        [JsonPropertyName("routing_template_step_id")]
        public long RoutingTemplateStepId { get; set; }

        [JsonPropertyName("routing_template_id")]
        public long RoutingTemplateId { get; set; }

        [JsonPropertyName("step_seq")]
        public int StepSeq { get; set; }

        [JsonPropertyName("process_id")]
        public long ProcessId { get; set; }

        [JsonPropertyName("default_process_type")]
        public string DefaultProcessType { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        // 화면 표시용 보강 필드 (백엔드 응답에는 없음)
        public string ProcessCode { get; set; } = string.Empty;
        public string ProcessName { get; set; } = string.Empty;
    }
}