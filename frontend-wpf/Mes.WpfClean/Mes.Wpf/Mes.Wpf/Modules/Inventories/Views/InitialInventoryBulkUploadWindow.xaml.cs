using Mes.Wpf.Modules.Inventories.ViewModels;
using System.Windows;

namespace Mes.Wpf.Modules.Inventories.Views
{
    public partial class InitialInventoryBulkUploadWindow : Window
    {
        public InitialInventoryBulkUploadWindow()
        {
            InitializeComponent();
            DataContextChanged += InitialInventoryBulkUploadWindow_DataContextChanged;
        }

        private InitialInventoryBulkUploadWindowViewModel? _viewModel;

        private void InitialInventoryBulkUploadWindow_DataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
        {
            if (_viewModel != null)
            {
                _viewModel.RequestClose -= Close;
            }

            _viewModel = e.NewValue as InitialInventoryBulkUploadWindowViewModel;

            if (_viewModel != null)
            {
                _viewModel.RequestClose += Close;
            }
        }
    }
}