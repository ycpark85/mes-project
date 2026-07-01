using Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels;
using System.Windows;
using System.Windows.Controls;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.Views
{
    public partial class OutsourceWorkGroupListPage : UserControl
    {
        private OutsourceWorkGroupListPageViewModel? _viewModel;

        public OutsourceWorkGroupListPage()
        {
            InitializeComponent();
            DataContextChanged += OutsourceWorkGroupListPage_DataContextChanged;
        }

        private void OutsourceWorkGroupListPage_DataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
        {
            if (_viewModel != null)
            {
                _viewModel.RequestOpenRawMaterialAllocation -= OpenRawMaterialAllocationWindow;
            }

            _viewModel = e.NewValue as OutsourceWorkGroupListPageViewModel;

            if (_viewModel != null)
            {
                _viewModel.RequestOpenRawMaterialAllocation += OpenRawMaterialAllocationWindow;
            }
        }

        private void OpenRawMaterialAllocationWindow(OutsourceRawMaterialAllocationWindowViewModel viewModel)
        {
            var window = new OutsourceRawMaterialAllocationWindow(viewModel)
            {
                Owner = Window.GetWindow(this)
            };

            if (window.ShowDialog() == true)
            {
                _viewModel?.ApplyEditRawMaterialAllocationDialog(viewModel);
            }
        }
    }
}
