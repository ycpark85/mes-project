using Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels;
using System.Windows;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.Views
{
    public partial class OutsourceRawMaterialAllocationWindow : Window
    {
        public OutsourceRawMaterialAllocationWindow(OutsourceRawMaterialAllocationWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            viewModel.OwnerWindow = this;
            Loaded += OutsourceRawMaterialAllocationWindow_Loaded;
        }

        private async void OutsourceRawMaterialAllocationWindow_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is OutsourceRawMaterialAllocationWindowViewModel viewModel)
            {
                await viewModel.InitializeAsync();
            }
        }
    }
}
