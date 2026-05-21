using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Auth.Dtos
{
    public class AuthMeResponse
    {
        [JsonPropertyName("user")]
        public AuthUserDto? User { get; set; }

        [JsonPropertyName("roles")]
        public List<AuthRoleDto> Roles { get; set; } = new();

        [JsonPropertyName("permissions")]
        public List<string> Permissions { get; set; } = new();
    }
}