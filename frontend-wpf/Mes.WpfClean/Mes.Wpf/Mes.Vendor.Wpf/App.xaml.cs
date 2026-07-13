using System;
using System.Windows;
using Mes.Vendor.Wpf.Infrastructure;
using Mes.Vendor.Wpf.ViewModels;
using Mes.Vendor.Wpf.Views;

namespace Mes.Vendor.Wpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var messages = new MessageService();

        try
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;

            var settings = AppSettings.Load();
            var apiClient = new ApiClient(settings.Api.BaseUrl);

            var loginViewModel = new LoginViewModel(apiClient);
            var loginWindow = new LoginWindow(loginViewModel);

            if (loginWindow.ShowDialog() != true || loginViewModel.LoginResponse == null)
            {
                Shutdown();
                return;
            }

            var mainViewModel = new MainViewModel(apiClient, messages, loginViewModel.LoginResponse);
            var mainWindow = new MainWindow(mainViewModel);

            MainWindow = mainWindow;
            ShutdownMode = ShutdownMode.OnMainWindowClose;
            mainWindow.Show();
        }
        catch (Exception ex)
        {
            messages.ShowError($"프로그램 시작 중 오류가 발생했습니다.\n\n{ex.Message}", "시작 오류");
            Shutdown();
        }
    }
}
