using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using Mes.Wpf.Modules.InspectionSchedules.ViewModels;

namespace Mes.Wpf.Modules.InspectionSchedules.Views
{
    public partial class InspectionResultWindow : Window
    {
        public InspectionResultWindow()
        {
            InitializeComponent();
        }

        public InspectionResultWindow(InspectionResultWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            viewModel.CloseRequested += OnCloseRequested;
        }

        private void OnCloseRequested(bool dialogResult)
        {
            DialogResult = dialogResult;
            Close();
        }

        private void DefectTypeIdTextBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            if (DataContext is not InspectionResultWindowViewModel vm)
            {
                return;
            }

            if (sender is not TextBox textBox || textBox.Tag is not InspectionResultDefectEditModel defect)
            {
                return;
            }

            OpenDefectTypeLookup(vm, defect);
            e.Handled = true;
        }

        private void OpenDefectTypeLookup(
            InspectionResultWindowViewModel vm,
            InspectionResultDefectEditModel defect)
        {
            var initialKeyword = defect.DefectTypeName;

            if (string.IsNullOrWhiteSpace(initialKeyword) && defect.DefectTypeId.HasValue)
            {
                initialKeyword = defect.DefectTypeId.Value.ToString();
            }

            var lookupVm = new DefectTypeLookupWindowViewModel(
                vm.ApiClient,
                vm.MessageService,
                initialKeyword);

            var lookupWindow = new DefectTypeLookupWindow(lookupVm)
            {
                Owner = this
            };

            if (lookupWindow.ShowDialog() == true && lookupWindow.SelectedDefectType != null)
            {
                vm.ApplySelectedDefectType(defect, lookupWindow.SelectedDefectType);
            }
        }
    }
}