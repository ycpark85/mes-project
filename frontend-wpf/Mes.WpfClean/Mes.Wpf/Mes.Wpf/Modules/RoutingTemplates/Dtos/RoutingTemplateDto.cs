using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.RoutingTemplates.Dtos
{
    public class RoutingTemplateDto
    {
        [JsonPropertyName("routing_template_id")]
        public long RoutingTemplateId { get; set; }

        [JsonPropertyName("template_code")]
        public string TemplateCode { get; set; } = string.Empty;

        [JsonPropertyName("template_name")]
        public string TemplateName { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }
    }
}