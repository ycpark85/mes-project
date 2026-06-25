using System.Windows;
using System.Windows.Input;
using Mes.Wpf.Modules.Auth.ViewModels;

namespace Mes.Wpf.Modules.Auth.Views
{
    public partial class LoginWindow : Window
    {
        private readonly LoginViewModel _viewModel;

        public LoginWindow(LoginViewModel viewModel)
        {
            InitializeComponent();

            _viewModel = viewModel;
            DataContext = _viewModel;

            _viewModel.LoginSucceeded += LoginViewModel_LoginSucceeded;

            Loaded += LoginWindow_Loaded;
        }

        private void LoginWindow_Loaded(object sender, RoutedEventArgs e)
        {
            Dispatcher.BeginInvoke(new Action(() =>
            {
                if (_viewModel.RememberLoginId && !string.IsNullOrWhiteSpace(_viewModel.LoginId))
                {
                    PasswordBox.Focus();
                    Keyboard.Focus(PasswordBox);
                    return;
                }

                LoginIdTextBox.Focus();
                LoginIdTextBox.SelectAll();
                Keyboard.Focus(LoginIdTextBox);
            }), System.Windows.Threading.DispatcherPriority.Input);
        }

        private void LoginButton_Click(object sender, RoutedEventArgs e)
        {
            ExecuteLogin();
        }

        private void PasswordBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            ExecuteLogin();
        }

        private void ExecuteLogin()
        {
            _viewModel.Password = PasswordBox.Password;

            if (!_viewModel.LoginCommand.CanExecute(null))
            {
                return;
            }

            _viewModel.LoginCommand.Execute(null);
        }

        private void LoginViewModel_LoginSucceeded(object? sender, System.EventArgs e)
        {
            DialogResult = true;
            Close();
        }
    }
}
