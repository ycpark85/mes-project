using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Processes.Dtos
{
    public class ProcessUpdateRequest
    {
        [JsonPropertyName("process_name")]
        public string? ProcessName { get; set; }

        [JsonPropertyName("process_type")]
        public string? ProcessType { get; set; }

        [JsonPropertyName("is_active")]
        public bool? IsActive { get; set; }
    }
}