using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Auth.Dtos;
using Mes.Wpf.Modules.MyPage.Dtos;
using System;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.MyPage.ViewModels
{
    public class PasswordChangeWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly bool _isRequired;

        private bool _isLoading;
        private string _errorMessage = string.Empty;

        public PasswordChangeWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            bool isRequired)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _isRequired = isRequired;
        }

        public event Action<AuthMeResponse>? PasswordChanged;

        public bool IsRequired => _isRequired;

        public string TitleText =>
            IsRequired
                ? "비밀번호 변경이 필요합니다"
                : "비밀번호 변경";

        public string DescriptionText =>
            IsRequired
                ? "초기 비밀번호로 로그인했습니다. 계속 사용하려면 비밀번호를 변경하세요."
                : "현재 비밀번호 확인 후 새 비밀번호로 변경합니다.";

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public string ErrorMessage
        {
            get => _errorMessage;
            set => SetProperty(ref _errorMessage, value);
        }

        public async Task ChangePasswordAsync(
            string currentPassword,
            string newPassword,
            string confirmPassword)
        {
            ErrorMessage = string.Empty;

            if (string.IsNullOrWhiteSpace(currentPassword))
            {
                ErrorMessage = "현재 비밀번호를 입력하세요.";
                return;
            }

            if (string.IsNullOrWhiteSpace(newPassword))
            {
                ErrorMessage = "새 비밀번호를 입력하세요.";
                return;
            }

            if (newPassword.Length < 6)
            {
                ErrorMessage = "새 비밀번호는 최소 6자리 이상입니다.";
                return;
            }

            if (newPassword != confirmPassword)
            {
                ErrorMessage = "새 비밀번호와 확인 비밀번호가 일치하지 않습니다.";
                return;
            }

            if (currentPassword == newPassword)
            {
                ErrorMessage = "새 비밀번호는 현재 비밀번호와 달라야 합니다.";
                return;
            }

            IsLoading = true;

            try
            {
                var request = new ChangePasswordRequest
                {
                    CurrentPassword = currentPassword,
                    NewPassword = newPassword
                };

                var result = await _apiClient.PatchAsync<ChangePasswordRequest, AuthMeResponse>(
                    ApiRoutes.AuthChangePassword,
                    request);

                if (!result.Success || result.Data == null)
                {
                    ErrorMessage = result.Message ?? "비밀번호 변경에 실패했습니다.";
                    return;
                }

                _messageService.ShowInfo("비밀번호가 변경되었습니다.");
                PasswordChanged?.Invoke(result.Data);
            }
            finally
            {
                IsLoading = false;
            }
        }

        public bool ConfirmCloseWithoutChange()
        {
            if (!IsRequired)
            {
                return true;
            }

            return _messageService.Confirm(
                "비밀번호를 변경하지 않으면 프로그램을 종료합니다.",
                "비밀번호 변경 필요");
        }
    }
}