using System;
using System.Windows;
using Mes.Wpf.Modules.Lots.ViewModels;

namespace Mes.Wpf.Modules.Lots.Views
{
    public partial class LotCreateWindow : Window
    {
        public LotCreateWindow(LotCreateWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
        }

        private LotCreateWindowViewModel? ViewModel =>
            DataContext as LotCreateWindowViewModel;

        private async void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            if (ViewModel == null)
            {
                return;
            }

            await ViewModel.SaveAsync();
        }

        private void ResetButton_Click(object sender, RoutedEventArgs e)
        {
            ViewModel?.ResetCommand.Execute(null);
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}