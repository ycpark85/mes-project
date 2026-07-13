using System.Windows;
using Mes.Vendor.Wpf.ViewModels;

namespace Mes.Vendor.Wpf.Views;

public partial class LoginWindow : Window
{
    private readonly LoginViewModel _viewModel;

    public LoginWindow(LoginViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = viewModel;
        viewModel.LoginSucceeded += (_, _) =>
        {
            DialogResult = true;
            Close();
        };
    }

    private void PasswordInput_OnPasswordChanged(object sender, RoutedEventArgs e)
    {
        _viewModel.Password = PasswordInput.Password;
    }
}
