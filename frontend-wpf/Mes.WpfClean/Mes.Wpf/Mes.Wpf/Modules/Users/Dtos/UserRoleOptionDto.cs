using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Users.Dtos
{
    public class UserRoleOptionDto
    {
        [JsonPropertyName("role_id")]
        public long RoleId { get; set; }

        [JsonPropertyName("role_code")]
        public string RoleCode { get; set; } = string.Empty;

        [JsonPropertyName("role_name")]
        public string RoleName { get; set; } = string.Empty;
    }
}