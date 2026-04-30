using System.Windows;
using Mes.Wpf.Modules.LotDetails.ViewModels;

namespace Mes.Wpf.Modules.LotDetails.Views
{
    public partial class LotDetailWindow : Window
    {
        private readonly LotDetailWindowViewModel _viewModel;

        public LotDetailWindow(LotDetailWindowViewModel viewModel)
        {
            InitializeComponent();

            _viewModel = viewModel;
            DataContext = _viewModel;

            _viewModel.RequestClose += OnRequestClose;
        }

        private void OnRequestClose()
        {
            Close();
        }

        protected override void OnClosed(System.EventArgs e)
        {
            _viewModel.RequestClose -= OnRequestClose;
            base.OnClosed(e);
        }
    }
}