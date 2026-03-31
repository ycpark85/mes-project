using System.Windows;
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
    }
}