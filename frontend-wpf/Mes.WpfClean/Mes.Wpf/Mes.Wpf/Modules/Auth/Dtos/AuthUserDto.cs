using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Auth.Dtos
{
    public class AuthUserDto
    {
        [JsonPropertyName("user_id")]
        public long UserId { get; set; }

        [JsonPropertyName("login_id")]
        public string LoginId { get; set; } = string.Empty;

        [JsonPropertyName("user_name")]
        public string UserName { get; set; } = string.Empty;

        [JsonPropertyName("department")]
        public string? Department { get; set; }

        [JsonPropertyName("position")]
        public string? Position { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("last_login_at")]
        public DateTime? LastLoginAt { get; set; }
    }
}