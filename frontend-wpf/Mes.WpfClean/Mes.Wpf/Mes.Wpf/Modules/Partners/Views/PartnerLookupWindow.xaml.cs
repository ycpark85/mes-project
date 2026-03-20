using Mes.Wpf.Modules.OrderLines.Dtos;
using Mes.Wpf.Modules.Partners.ViewModels;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace Mes.Wpf.Modules.Partners.Views
{
    public partial class PartnerLookupWindow : Window
    {
        public PartnerLookupWindow(PartnerLookupWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            Loaded += PartnerLookupWindow_Loaded;
        }

        public OrderLinePartnerLookupDto? SelectedPartner { get; private set; }

        private async void PartnerLookupWindow_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is PartnerLookupWindowViewModel vm)
            {
                await vm.InitializeAsync();
            }
        }

        private void SelectButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not PartnerLookupWindowViewModel vm || vm.SelectedItem == null)
            {
                return;
            }

            SelectedPartner = vm.SelectedItem;
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