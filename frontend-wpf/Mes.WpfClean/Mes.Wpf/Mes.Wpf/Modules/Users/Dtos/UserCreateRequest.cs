using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Users.Dtos
{
    public class UserCreateRequest
    {
        [JsonPropertyName("login_id")]
        public string LoginId { get; set; } = string.Empty;

        [JsonPropertyName("user_name")]
        public string UserName { get; set; } = string.Empty;

        [JsonPropertyName("password")]
        public string Password { get; set; } = string.Empty;

        [JsonPropertyName("role_ids")]
        public List<long> RoleIds { get; set; } = new();

        [JsonPropertyName("department")]
        public string? Department { get; set; }

        [JsonPropertyName("position")]
        public string? Position { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; } = true;

        [JsonPropertyName("is_vendor_user")]
        public bool IsVendorUser { get; set; }

        [JsonPropertyName("vendor_partner_id")]
        public long? VendorPartnerId { get; set; }

        [JsonPropertyName("vendor_access_active")]
        public bool VendorAccessActive { get; set; } = true;
    }
}
