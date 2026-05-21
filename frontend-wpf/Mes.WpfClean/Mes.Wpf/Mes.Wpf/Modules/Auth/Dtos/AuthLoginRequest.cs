using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Auth.Dtos
{
    public class AuthLoginRequest
    {
        [JsonPropertyName("login_id")]
        public string LoginId { get; set; } = string.Empty;

        [JsonPropertyName("password")]
        public string Password { get; set; } = string.Empty;
    }
}