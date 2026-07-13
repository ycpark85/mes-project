using System;
using System.Windows.Input;
using Mes.Vendor.Wpf.Core;
using Mes.Vendor.Wpf.Dtos;
using Mes.Vendor.Wpf.Infrastructure;

namespace Mes.Vendor.Wpf.ViewModels;

public sealed class LoginViewModel : BindableBase
{
    private const string LoginRoute = "api/v1/auth/login";

    private readonly ApiClient _apiClient;
    private string _loginId = string.Empty;
    private string _password = string.Empty;
    private string _errorMessage = string.Empty;
    private bool _isLoading;

    public LoginViewModel(ApiClient apiClient)
    {
        _apiClient = apiClient;
        LoginCommand = new AsyncRelayCommand(LoginAsync, CanLogin);
    }

    public event EventHandler? LoginSucceeded;

    public ICommand LoginCommand { get; }

    public AuthLoginResponse? LoginResponse { get; private set; }

    public string LoginId
    {
        get => _loginId;
        set
        {
            if (SetProperty(ref _loginId, value))
            {
                RaiseCommandStateChanged();
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
                RaiseCommandStateChanged();
            }
        }
    }

    public string ErrorMessage
    {
        get => _errorMessage;
        private set => SetProperty(ref _errorMessage, value);
    }

    public bool IsLoading
    {
        get => _isLoading;
        private set
        {
            if (SetProperty(ref _isLoading, value))
            {
                RaiseCommandStateChanged();
            }
        }
    }

    private bool CanLogin()
    {
        return !IsLoading
            && !string.IsNullOrWhiteSpace(LoginId)
            && !string.IsNullOrWhiteSpace(Password);
    }

    private async Task LoginAsync()
    {
        ErrorMessage = string.Empty;
        IsLoading = true;

        try
        {
            var result = await _apiClient.PostAsync<AuthLoginRequest, AuthLoginResponse>(
                LoginRoute,
                new AuthLoginRequest
                {
                    LoginId = LoginId.Trim(),
                    Password = Password
                });

            if (!result.Success || result.Data is null || string.IsNullOrWhiteSpace(result.Data.AccessToken))
            {
                ErrorMessage = result.Message ?? "로그인에 실패했습니다.";
                _apiClient.ClearAccessToken();
                return;
            }

            LoginResponse = result.Data;
            _apiClient.SetAccessToken(result.Data.AccessToken);
            LoginSucceeded?.Invoke(this, EventArgs.Empty);
        }
        finally
        {
            IsLoading = false;
        }
    }

    private void RaiseCommandStateChanged()
    {
        if (LoginCommand is AsyncRelayCommand command)
        {
            command.RaiseCanExecuteChanged();
        }
    }
}
