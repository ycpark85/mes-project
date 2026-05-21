using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class RolePermissionResponse
    {
        [JsonPropertyName("role_id")]
        public long RoleId { get; set; }

        [JsonPropertyName("permissions")]
        public List<PermissionDto> Permissions { get; set; } = new();
    }
}