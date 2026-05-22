using Mes.Wpf.Modules.Auth.Dtos;
using Mes.Wpf.Modules.MyPage.ViewModels;
using System.ComponentModel;
using System.Windows;

namespace Mes.Wpf.Modules.MyPage.Views
{
    public partial class PasswordChangeWindow : Window
    {
        private readonly PasswordChangeWindowViewModel _viewModel;
        private bool _passwordChanged;

        public PasswordChangeWindow(PasswordChangeWindowViewModel viewModel)
        {
            InitializeComponent();

            _viewModel = viewModel;
            DataContext = _viewModel;

            _viewModel.PasswordChanged += OnPasswordChanged;
        }

        public AuthMeResponse? ChangedAuthContext { get; private set; }

        private async void ChangeButton_Click(object sender, RoutedEventArgs e)
        {
            await _viewModel.ChangePasswordAsync(
                CurrentPasswordBox.Password,
                NewPasswordBox.Password,
                ConfirmPasswordBox.Password);
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void OnPasswordChanged(AuthMeResponse response)
        {
            _passwordChanged = true;
            ChangedAuthContext = response;

            DialogResult = true;
            Close();
        }

        private void Window_Closing(object sender, CancelEventArgs e)
        {
            if (_viewModel.IsRequired && !_passwordChanged)
            {
                var canClose = _viewModel.ConfirmCloseWithoutChange();

                if (!canClose)
                {
                    e.Cancel = true;
                }
            }
        }

        protected override void OnClosed(System.EventArgs e)
        {
            _viewModel.PasswordChanged -= OnPasswordChanged;

            base.OnClosed(e);
        }
    }
}