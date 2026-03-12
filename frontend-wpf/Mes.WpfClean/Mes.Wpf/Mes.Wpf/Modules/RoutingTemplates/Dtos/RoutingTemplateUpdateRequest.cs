using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.RoutingTemplates.Dtos
{
    public class RoutingTemplateUpdateRequest
    {
        [JsonPropertyName("template_name")]
        public string TemplateName { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }
    }
}