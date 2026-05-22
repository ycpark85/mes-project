using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.MyPage.Dtos
{
    public class ChangePasswordRequest
    {
        [JsonPropertyName("current_password")]
        public string CurrentPassword { get; set; } = string.Empty;

        [JsonPropertyName("new_password")]
        public string NewPassword { get; set; } = string.Empty;
    }
}