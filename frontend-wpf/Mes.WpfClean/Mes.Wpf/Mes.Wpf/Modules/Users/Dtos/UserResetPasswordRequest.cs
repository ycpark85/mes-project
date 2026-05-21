using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Users.Dtos
{
    public class UserResetPasswordRequest
    {
        [JsonPropertyName("new_password")]
        public string NewPassword { get; set; } = string.Empty;
    }
}