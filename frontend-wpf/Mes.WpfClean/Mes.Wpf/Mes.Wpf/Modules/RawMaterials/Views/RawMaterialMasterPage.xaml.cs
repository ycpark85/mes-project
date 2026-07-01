using Mes.Wpf.Modules.Partners.ViewModels;
using Mes.Wpf.Modules.Partners.Views;
using Mes.Wpf.Modules.RawMaterials.ViewModels;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace Mes.Wpf.Modules.RawMaterials.Views
{
    public partial class RawMaterialMasterPage : UserControl
    {
        public RawMaterialMasterPage()
        {
            InitializeComponent();
        }

        private void PartnerSearchButton_Click(object sender, RoutedEventArgs e)
        {
            OpenPartnerLookup();
        }

        private void PartnerNameTextBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            OpenPartnerLookup();
            e.Handled = true;
        }

        private void OpenPartnerLookup()
        {
            if (DataContext is not RawMaterialMasterPageViewModel vm)
            {
                return;
            }

            var lookupVm = new PartnerLookupWindowViewModel(
                vm.ApiClient,
                vm.MessageService,
                vm.LocationEditModel.PartnerName);

            var window = new PartnerLookupWindow(lookupVm)
            {
                Owner = Window.GetWindow(this)
            };

            if (window.ShowDialog() == true && window.SelectedPartner != null)
            {
                vm.ApplySelectedPartner(window.SelectedPartner);
            }
        }
    }
}
