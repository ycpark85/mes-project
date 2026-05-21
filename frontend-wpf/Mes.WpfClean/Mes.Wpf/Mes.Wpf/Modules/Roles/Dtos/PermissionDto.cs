using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class PermissionDto
    {
        [JsonPropertyName("permission_id")]
        public long PermissionId { get; set; }

        [JsonPropertyName("permission_code")]
        public string PermissionCode { get; set; } = string.Empty;

        [JsonPropertyName("menu_code")]
        public string MenuCode { get; set; } = string.Empty;

        [JsonPropertyName("action_code")]
        public string ActionCode { get; set; } = string.Empty;

        [JsonPropertyName("permission_name")]
        public string PermissionName { get; set; } = string.Empty;

        [JsonPropertyName("sort_order")]
        public int SortOrder { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime? CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime? UpdatedAt { get; set; }
    }
}