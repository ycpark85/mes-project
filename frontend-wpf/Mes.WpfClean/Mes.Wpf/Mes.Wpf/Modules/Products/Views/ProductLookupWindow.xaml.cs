using Mes.Wpf.Modules.OrderLines.Dtos;
using Mes.Wpf.Modules.Products.ViewModels;
using System.Windows;
using System.Windows.Input;

namespace Mes.Wpf.Modules.Products.Views
{
    public partial class ProductLookupWindow : Window
    {
        public ProductLookupWindow(ProductLookupWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            Loaded += ProductLookupWindow_Loaded;
        }

        public OrderLineProductLookupDto? SelectedProduct { get; private set; }

        private async void ProductLookupWindow_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProductLookupWindowViewModel vm)
            {
                await vm.InitializeAsync();
            }
        }

        private void SelectButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not ProductLookupWindowViewModel vm || vm.SelectedItem == null)
            {
                return;
            }

            SelectedProduct = vm.SelectedItem;
            DialogResult = true;
            Close();
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        private void DataGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
        {
            SelectButton_Click(sender, e);
        }
    }
}