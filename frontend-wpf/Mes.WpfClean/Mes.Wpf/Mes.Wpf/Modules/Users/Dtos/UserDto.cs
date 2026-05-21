using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Users.Dtos
{
    public class UserDto
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

        [JsonPropertyName("created_at")]
        public DateTime? CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime? UpdatedAt { get; set; }

        [JsonPropertyName("roles")]
        public List<UserRoleDto> Roles { get; set; } = new();

        public string RoleNames
        {
            get
            {
                if (Roles == null || Roles.Count == 0)
                {
                    return string.Empty;
                }

                return string.Join(", ", Roles.Select(x => x.RoleName));
            }
        }

        public string UseYn => IsActive ? "사용" : "미사용";
    }
}