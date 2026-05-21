using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Auth.Dtos
{
    public class AuthLoginResponse
    {
        [JsonPropertyName("access_token")]
        public string AccessToken { get; set; } = string.Empty;

        [JsonPropertyName("token_type")]
        public string TokenType { get; set; } = string.Empty;

        [JsonPropertyName("expires_in_minutes")]
        public int ExpiresInMinutes { get; set; }

        [JsonPropertyName("user")]
        public AuthUserDto? User { get; set; }

        [JsonPropertyName("roles")]
        public List<AuthRoleDto> Roles { get; set; } = new();

        [JsonPropertyName("permissions")]
        public List<string> Permissions { get; set; } = new();
    }
}