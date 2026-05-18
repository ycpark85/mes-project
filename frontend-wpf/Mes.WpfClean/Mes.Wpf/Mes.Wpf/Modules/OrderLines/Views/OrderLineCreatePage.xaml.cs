using Mes.Wpf.Modules.OrderLineList.ViewModels;
using Mes.Wpf.Modules.OrderLineList.Views;
using Mes.Wpf.Modules.OrderLines.Dtos;
using Mes.Wpf.Modules.OrderLines.ViewModels;
using Mes.Wpf.Modules.Partners.ViewModels;
using Mes.Wpf.Modules.Partners.Views;
using Mes.Wpf.Modules.Products.ViewModels;
using Mes.Wpf.Modules.Products.Views;
using Mes.Wpf.Views.Shell;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;

namespace Mes.Wpf.Modules.OrderLines.Views
{
    public partial class OrderLineCreatePage : UserControl
    {
        public OrderLineCreatePage()
        {
            InitializeComponent();
        }

        private void PartnerSearchButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not OrderLineCreatePageViewModel vm)
            {
                return;
            }

            var lookupVm = new PartnerLookupWindowViewModel(
                vm.ApiClient,
                vm.MessageService,
                vm.Header.PartnerName);

            var window = new PartnerLookupWindow(lookupVm)
            {
                Owner = Window.GetWindow(this)
            };

            if (window.ShowDialog() == true && window.SelectedPartner != null)
            {
                vm.ApplySelectedPartner(window.SelectedPartner);
            }
        }

        private void ProductSearchButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not OrderLineCreatePageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.Tag is not OrderLineCreateLineEditModel line)
            {
                return;
            }

            var keyword = line.ProductCode;

            //var keyword = !string.IsNullOrWhiteSpace(line.ProductCode)
            //    ? line.ProductCode
            //    : line.ProductName;

            var lookupVm = new ProductLookupWindowViewModel(
                vm.ApiClient,
                vm.MessageService,
                keyword);

            var window = new ProductLookupWindow(lookupVm)
            {
                Owner = Window.GetWindow(this)
            };

            if (window.ShowDialog() == true && window.SelectedProduct != null)
            {
                vm.ApplySelectedProduct(line, window.SelectedProduct);
            }
        }

        private void RemoveLineButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not OrderLineCreatePageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.Tag is not OrderLineCreateLineEditModel line)
            {
                return;
            }

            vm.RemoveLine(line);
        }

        private void OrderQtyTextBox_LostFocus(object sender, RoutedEventArgs e)
        {
            if (DataContext is not OrderLineCreatePageViewModel vm)
            {
                return;
            }

            vm.RefreshSummary();
        }

        private void ProductCodeTextBox_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
        {
            if (e.Key != System.Windows.Input.Key.Enter)
            {
                return;
            }

            if (DataContext is not OrderLineCreatePageViewModel vm)
            {
                return;
            }

            if (sender is not TextBox textBox)
            {
                return;
            }

            if (textBox.DataContext is not OrderLineCreateLineEditModel line)
            {
                return;
            }

            var keyword = line.ProductCode?.Trim();

            if (string.IsNullOrWhiteSpace(keyword))
            {
                return;
            }

            var lookupVm = new ProductLookupWindowViewModel(
                vm.ApiClient,
                vm.MessageService,
                keyword);

            var window = new ProductLookupWindow(lookupVm)
            {
                Owner = Window.GetWindow(this)
            };

            if (window.ShowDialog() == true && window.SelectedProduct != null)
            {
                vm.ApplySelectedProduct(line, window.SelectedProduct);
            }

            e.Handled = true;
        }
        private async void DrawingOpenButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not OrderLineCreatePageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.Tag is not OrderLineCreateLineEditModel line)
            {
                return;
            }

            await vm.ViewDrawingAsync(line);
        }

        private async void OpenBulkImportPage_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not OrderLineCreatePageViewModel currentVm)
            {
                return;
            }

            var bulkVm = new OrderLineBulkImportPageViewModel(
                currentVm.ApiClient,
                currentVm.MessageService,
                () => new OrderLineListPage
                {
                    DataContext = new OrderLineListPageViewModel(
                        currentVm.ApiClient,
                        currentVm.MessageService)
                });

            var bulkPage = new OrderLineBulkImportPage
            {
                DataContext = bulkVm
            };

            await bulkVm.InitializeAsync();

            if (Application.Current.MainWindow is MainWindow mainWindow)
            {
                mainWindow.MainContent.Content = bulkPage;
            }
        }

    }
}

