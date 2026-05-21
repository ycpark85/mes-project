using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class RoleEditModel : ViewModelBase
    {
        private long? _roleId;
        private string _roleCode = string.Empty;
        private string _roleName = string.Empty;
        private string _description = string.Empty;
        private bool _isSystem;
        private bool _isActive = true;

        public long? RoleId
        {
            get => _roleId;
            set => SetProperty(ref _roleId, value);
        }

        public string RoleCode
        {
            get => _roleCode;
            set => SetProperty(ref _roleCode, value);
        }

        public string RoleName
        {
            get => _roleName;
            set => SetProperty(ref _roleName, value);
        }

        public string Description
        {
            get => _description;
            set => SetProperty(ref _description, value);
        }

        public bool IsSystem
        {
            get => _isSystem;
            set => SetProperty(ref _isSystem, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(RoleDto dto)
        {
            RoleId = dto.RoleId;
            RoleCode = dto.RoleCode;
            RoleName = dto.RoleName;
            Description = dto.Description ?? string.Empty;
            IsSystem = dto.IsSystem;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            RoleId = null;
            RoleCode = string.Empty;
            RoleName = string.Empty;
            Description = string.Empty;
            IsSystem = false;
            IsActive = true;
        }
    }
}