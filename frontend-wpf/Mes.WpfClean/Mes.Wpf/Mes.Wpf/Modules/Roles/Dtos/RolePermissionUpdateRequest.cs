using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class RolePermissionUpdateRequest
    {
        [JsonPropertyName("permission_ids")]
        public List<long> PermissionIds { get; set; } = new();
    }
}