using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class RoleCreateRequest
    {
        [JsonPropertyName("role_code")]
        public string RoleCode { get; set; } = string.Empty;

        [JsonPropertyName("role_name")]
        public string RoleName { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;
    }
}