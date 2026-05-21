using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class RoleUpdateRequest
    {
        [JsonPropertyName("role_name")]
        public string? RoleName { get; set; }

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("is_active")]
        public bool? IsActive { get; set; }
    }
}