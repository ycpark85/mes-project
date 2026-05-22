using Mes.Wpf.Core.Common;
using Mes.Wpf.Modules.Auth.Dtos;
using System;
using System.Windows.Input;

namespace Mes.Wpf.Modules.MyPage.ViewModels
{
    public class MyPageViewModel : ViewModelBase
    {
        private readonly Func<bool, bool> _openPasswordChangeWindow;
        private AuthUserDto? _user;

        public MyPageViewModel(
            AuthUserDto? user,
            Func<bool, bool> openPasswordChangeWindow)
        {
            _user = user;
            _openPasswordChangeWindow = openPasswordChangeWindow;

            ChangePasswordCommand = new RelayCommand(_ => OpenPasswordChange());
        }

        public ICommand ChangePasswordCommand { get; }

        public string LoginId => _user?.LoginId ?? "-";

        public string UserName => _user?.UserName ?? "-";

        public string Department =>
            string.IsNullOrWhiteSpace(_user?.Department)
                ? "-"
                : _user!.Department!;

        public string Position =>
            string.IsNullOrWhiteSpace(_user?.Position)
                ? "-"
                : _user!.Position!;

        public string PasswordChangeRequiredText =>
            _user?.PasswordChangeRequired == true ? "필요" : "-";

        public void UpdateUser(AuthUserDto? user)
        {
            _user = user;

            OnPropertyChanged(nameof(LoginId));
            OnPropertyChanged(nameof(UserName));
            OnPropertyChanged(nameof(Department));
            OnPropertyChanged(nameof(Position));
            OnPropertyChanged(nameof(PasswordChangeRequiredText));
        }

        private void OpenPasswordChange()
        {
            var changed = _openPasswordChangeWindow(false);

            if (changed && _user != null)
            {
                _user.PasswordChangeRequired = false;
                OnPropertyChanged(nameof(PasswordChangeRequiredText));
            }
        }
    }
}