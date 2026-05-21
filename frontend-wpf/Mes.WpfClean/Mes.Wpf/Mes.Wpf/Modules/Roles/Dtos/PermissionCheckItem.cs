using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Roles.Dtos
{
    public class PermissionCheckItem : ViewModelBase
    {
        private bool _isSelected;

        public long PermissionId { get; set; }

        public string PermissionCode { get; set; } = string.Empty;

        public string MenuCode { get; set; } = string.Empty;

        public string ActionCode { get; set; } = string.Empty;

        public string PermissionName { get; set; } = string.Empty;

        public int SortOrder { get; set; }

        public string DisplayName => $"{PermissionCode} - {PermissionName}";

        public bool IsSelected
        {
            get => _isSelected;
            set => SetProperty(ref _isSelected, value);
        }

        public void LoadFromDto(PermissionDto dto)
        {
            PermissionId = dto.PermissionId;
            PermissionCode = dto.PermissionCode;
            MenuCode = dto.MenuCode;
            ActionCode = dto.ActionCode;
            PermissionName = dto.PermissionName;
            SortOrder = dto.SortOrder;
            IsSelected = false;
        }
    }
}