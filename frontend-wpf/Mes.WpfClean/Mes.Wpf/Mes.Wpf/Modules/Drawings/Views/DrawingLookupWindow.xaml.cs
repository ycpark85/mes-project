using System.Windows;
using System.Windows.Input;
using Mes.Wpf.Modules.Drawings.Dtos;
using Mes.Wpf.Modules.Drawings.ViewModels;

namespace Mes.Wpf.Modules.Drawings.Views
{
    public partial class DrawingLookupWindow : Window
    {
        public DrawingLookupWindow(DrawingLookupWindowViewModel viewModel)
        {
            InitializeComponent();

            DataContext = viewModel;
            Loaded += DrawingLookupWindow_Loaded;
        }

        public DrawingDto? SelectedDrawing { get; private set; }

        private async void DrawingLookupWindow_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is DrawingLookupWindowViewModel vm)
            {
                await vm.InitializeAsync();
            }
        }

        private void SelectButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not DrawingLookupWindowViewModel vm || vm.SelectedItem == null)
            {
                return;
            }

            SelectedDrawing = vm.SelectedItem;
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

        private async void KeywordTextBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key != Key.Enter)
            {
                return;
            }

            if (DataContext is DrawingLookupWindowViewModel vm)
            {
                await vm.SearchAsync();
            }

            e.Handled = true;
        }
    }
}