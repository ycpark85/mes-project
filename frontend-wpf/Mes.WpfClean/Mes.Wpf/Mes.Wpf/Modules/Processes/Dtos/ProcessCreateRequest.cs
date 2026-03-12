using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Processes.Dtos
{
    public class ProcessCreateRequest
    {
        [JsonPropertyName("process_code")]
        public string ProcessCode { get; set; } = string.Empty;

        [JsonPropertyName("process_name")]
        public string ProcessName { get; set; } = string.Empty;

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = "INTERNAL";

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;
    }
}