using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Users.Dtos
{
    public class UserRoleCheckItem : ViewModelBase
    {
        private bool _isSelected;

        public long RoleId { get; set; }

        public string RoleCode { get; set; } = string.Empty;

        public string RoleName { get; set; } = string.Empty;

        public string DisplayName => $"{RoleCode} - {RoleName}";

        public bool IsSelected
        {
            get => _isSelected;
            set => SetProperty(ref _isSelected, value);
        }

        public void LoadFromDto(UserRoleOptionDto dto)
        {
            RoleId = dto.RoleId;
            RoleCode = dto.RoleCode;
            RoleName = dto.RoleName;
        }
    }
}