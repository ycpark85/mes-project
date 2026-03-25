using Mes.Wpf.Modules.Lots.ViewModels;
using System.Windows;

namespace Mes.Wpf.Modules.Lots.Views
{
    public partial class LotCreateWindow : Window
    {
        public LotCreateWindow(LotCreateWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
        }

        private void ReworkCheckBox_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is LotCreateWindowViewModel vm)
            {
                vm.ToggleReworkCommand.Execute(null);
            }
        }

        private void ResetButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is LotCreateWindowViewModel vm)
            {
                vm.ResetCommand.Execute(null);
            }
        }

        private async void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is LotCreateWindowViewModel vm)
            {
                await vm.SaveAsync();
            }
        }

        private async void OpenDrawingFileButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is LotCreateWindowViewModel vm)
            {
                await vm.OpenDrawingFileAsync();
            }
        }

        private async void OpenOriginalFileButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is LotCreateWindowViewModel vm)
            {
                await vm.OpenOriginalFileAsync();
            }
        }

        private async void OpenPlateWorkButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is LotCreateWindowViewModel vm)
            {
                await vm.OpenPlateWorkAsync();
            }
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}