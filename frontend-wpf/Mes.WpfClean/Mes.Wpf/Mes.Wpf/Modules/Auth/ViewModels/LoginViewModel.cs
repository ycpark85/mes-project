using System;
using System.Threading.Tasks;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Auth.Dtos;

namespace Mes.Wpf.Modules.Auth.ViewModels
{
    public class LoginViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _loginId = string.Empty;
        private string _password = string.Empty;
        private string _errorMessage = string.Empty;
        private bool _isLoading;

        public LoginViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            LoginCommand = new AsyncRelayCommand(LoginAsync, CanLogin);
        }

        public event EventHandler? LoginSucceeded;

        public AsyncRelayCommand LoginCommand { get; }

        public AuthLoginResponse? LoginResponse { get; private set; }

        public string LoginId
        {
            get => _loginId;
            set
            {
                if (SetProperty(ref _loginId, value))
                {
                    LoginCommand.RaiseCanExecuteChanged();
                }
            }
        }

        public string Password
        {
            get => _password;
            set
            {
                if (SetProperty(ref _password, value))
                {
                    LoginCommand.RaiseCanExecuteChanged();
                }
            }
        }

        public string ErrorMessage
        {
            get => _errorMessage;
            set => SetProperty(ref _errorMessage, value);
        }

        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (SetProperty(ref _isLoading, value))
                {
                    LoginCommand.RaiseCanExecuteChanged();
                }
            }
        }

        private bool CanLogin()
        {
            if (IsLoading)
            {
                return false;
            }

            return !string.IsNullOrWhiteSpace(LoginId)
                && !string.IsNullOrWhiteSpace(Password);
        }

        private async Task LoginAsync()
        {
            Normalize();

            if (!Validate())
            {
                return;
            }

            IsLoading = true;
            ErrorMessage = string.Empty;

            try
            {
                _apiClient.ClearAccessToken();

                var request = new AuthLoginRequest
                {
                    LoginId = LoginId,
                    Password = Password
                };

                var result = await _apiClient.PostAsync<AuthLoginRequest, AuthLoginResponse>(
                    ApiRoutes.AuthLogin,
                    request);

                if (!result.Success || result.Data == null)
                {
                    ErrorMessage = result.Message ?? "로그인에 실패했습니다.";
                    return;
                }

                if (string.IsNullOrWhiteSpace(result.Data.AccessToken))
                {
                    ErrorMessage = "로그인 응답에 토큰 정보가 없습니다.";
                    return;
                }

                _apiClient.SetAccessToken(result.Data.AccessToken);

                LoginResponse = result.Data;
                LoginSucceeded?.Invoke(this, EventArgs.Empty);
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void Normalize()
        {
            LoginId = LoginId.Trim();
        }

        private bool Validate()
        {
            if (string.IsNullOrWhiteSpace(LoginId))
            {
                ErrorMessage = "아이디를 입력하세요.";
                return false;
            }

            if (string.IsNullOrWhiteSpace(Password))
            {
                ErrorMessage = "비밀번호를 입력하세요.";
                return false;
            }

            if (Password.Length < 6)
            {
                ErrorMessage = "비밀번호는 최소 6자리 이상입니다.";
                return false;
            }

            return true;
        }
    }
}