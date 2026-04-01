using System.Windows;
using System.Windows.Input;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using Mes.Wpf.Modules.InspectionSchedules.ViewModels;

namespace Mes.Wpf.Modules.InspectionSchedules.Views
{
    public partial class DefectTypeLookupWindow : Window
    {
        public DefectTypeLookupWindow(DefectTypeLookupWindowViewModel viewModel)
        {
            InitializeComponent();
            DataContext = viewModel;
            Loaded += DefectTypeLookupWindow_Loaded;
        }

        public InspectionResultDefectTypeLookupDto? SelectedDefectType { get; private set; }

        private async void DefectTypeLookupWindow_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is DefectTypeLookupWindowViewModel vm)
            {
                await vm.InitializeAsync();
            }
        }

        private async void SearchButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is DefectTypeLookupWindowViewModel vm)
            {
                await vm.SearchAsync();
            }
        }

        private async void KeywordTextBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            if (DataContext is DefectTypeLookupWindowViewModel vm)
            {
                await vm.SearchAsync();
                e.Handled = true;
            }
        }

        private void SelectButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not DefectTypeLookupWindowViewModel vm || vm.SelectedItem == null)
            {
                return;
            }

            SelectedDefectType = vm.SelectedItem;
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