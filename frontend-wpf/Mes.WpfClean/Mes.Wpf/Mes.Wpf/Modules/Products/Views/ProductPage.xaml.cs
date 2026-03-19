using Mes.Wpf.Modules.Drawings.Dtos;
using Mes.Wpf.Modules.Products.ViewModels;
using System.Windows;
using System.Windows.Controls;

namespace Mes.Wpf.Modules.Products.Views
{
    public partial class ProductPage : UserControl
    {
        public ProductPage()
        {
            InitializeComponent();
        }

        private void BulkUpload_Click(object sender, RoutedEventArgs e)
        {
            var window = new ProductBulkUploadWindow
            {
                Owner = Window.GetWindow(this),
                DataContext = DataContext
            };

            window.ShowDialog();
        }

        
        private void DrawingSearchResult_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (DataContext is ProductPageViewModel vm
                && sender is ListBox listBox
                && listBox.SelectedItem is DrawingDto drawing)
            {
                vm.SelectDrawing(drawing);
                listBox.SelectedItem = null;
            }
        }
    }
}