using System.Collections.Generic;
using System.Linq;
using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Users.Dtos
{
    public class UserEditModel : ViewModelBase
    {
        private long? _userId;
        private string _loginId = string.Empty;
        private string _userName = string.Empty;
        private string _initialPassword = string.Empty;
        private string _resetPassword = string.Empty;
        private string _department = string.Empty;
        private string _position = string.Empty;
        private bool _isActive = true;
        private bool _isVendorUser;
        private long? _vendorPartnerId;
        private bool _vendorAccessActive = true;
        private List<long> _roleIds = new();

        public long? UserId
        {
            get => _userId;
            set => SetProperty(ref _userId, value);
        }

        public string LoginId
        {
            get => _loginId;
            set => SetProperty(ref _loginId, value);
        }

        public string UserName
        {
            get => _userName;
            set => SetProperty(ref _userName, value);
        }

        public string InitialPassword
        {
            get => _initialPassword;
            set => SetProperty(ref _initialPassword, value);
        }

        public string ResetPassword
        {
            get => _resetPassword;
            set => SetProperty(ref _resetPassword, value);
        }

        public string Department
        {
            get => _department;
            set => SetProperty(ref _department, value);
        }

        public string Position
        {
            get => _position;
            set => SetProperty(ref _position, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public bool IsVendorUser
        {
            get => _isVendorUser;
            set => SetProperty(ref _isVendorUser, value);
        }

        public long? VendorPartnerId
        {
            get => _vendorPartnerId;
            set => SetProperty(ref _vendorPartnerId, value);
        }

        public bool VendorAccessActive
        {
            get => _vendorAccessActive;
            set => SetProperty(ref _vendorAccessActive, value);
        }

        public List<long> RoleIds
        {
            get => _roleIds;
            set => SetProperty(ref _roleIds, value);
        }

        public void LoadFromDto(UserDto dto)
        {
            UserId = dto.UserId;
            LoginId = dto.LoginId;
            UserName = dto.UserName;
            InitialPassword = string.Empty;
            ResetPassword = string.Empty;
            Department = dto.Department ?? string.Empty;
            Position = dto.Position ?? string.Empty;
            IsActive = dto.IsActive;
            IsVendorUser = dto.VendorAccess != null;
            VendorPartnerId = dto.VendorAccess?.PartnerId;
            VendorAccessActive = dto.VendorAccess?.IsActive ?? true;
            RoleIds = dto.Roles?.Select(x => x.RoleId).ToList() ?? new List<long>();
        }

        public void Clear()
        {
            UserId = null;
            LoginId = string.Empty;
            UserName = string.Empty;
            InitialPassword = string.Empty;
            ResetPassword = string.Empty;
            Department = string.Empty;
            Position = string.Empty;
            IsActive = true;
            IsVendorUser = false;
            VendorPartnerId = null;
            VendorAccessActive = true;
            RoleIds = new List<long>();
        }
    }
}
