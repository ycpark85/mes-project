using System;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class RoleDto
    {
        [JsonPropertyName("role_id")]
        public long RoleId { get; set; }

        [JsonPropertyName("role_code")]
        public string RoleCode { get; set; } = string.Empty;

        [JsonPropertyName("role_name")]
        public string RoleName { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("is_system")]
        public bool IsSystem { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime? CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime? UpdatedAt { get; set; }

        public string UseYn => IsActive ? "사용" : "미사용";

        public string SystemYn => IsSystem ? "시스템" : "일반";
    }
}