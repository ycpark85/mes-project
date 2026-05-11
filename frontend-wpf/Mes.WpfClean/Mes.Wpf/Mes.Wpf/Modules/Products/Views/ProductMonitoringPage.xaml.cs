using System.Windows;
using System.Windows.Controls;
using Mes.Wpf.Modules.LotDetails.ViewModels;
using Mes.Wpf.Modules.LotDetails.Views;
using Mes.Wpf.Modules.Products.Dtos;
using Mes.Wpf.Modules.Products.ViewModels;

namespace Mes.Wpf.Modules.Products.Views
{
    public partial class ProductMonitoringPage : UserControl
    {
        private ProductMonitoringPageViewModel? _viewModel;

        public ProductMonitoringPage()
        {
            InitializeComponent();

            Loaded += ProductMonitoringPage_Loaded;
            Unloaded += ProductMonitoringPage_Unloaded;
        }

        private void ProductMonitoringPage_Loaded(object sender, RoutedEventArgs e)
        {
            if (DataContext is not ProductMonitoringPageViewModel vm)
            {
                return;
            }

            if (_viewModel == vm)
            {
                return;
            }

            if (_viewModel != null)
            {
                _viewModel.RequestOpenLotDetail -= OnRequestOpenLotDetail;
            }

            _viewModel = vm;
            _viewModel.RequestOpenLotDetail += OnRequestOpenLotDetail;
        }

        private void ProductMonitoringPage_Unloaded(object sender, RoutedEventArgs e)
        {
            if (_viewModel != null)
            {
                _viewModel.RequestOpenLotDetail -= OnRequestOpenLotDetail;
                _viewModel = null;
            }
        }

        private async void OnRequestOpenLotDetail(long lotId)
        {
            if (_viewModel == null)
            {
                return;
            }

            var windowVm = new LotDetailWindowViewModel(
                _viewModel.ApiClient,
                _viewModel.MessageService);

            await windowVm.InitializeAsync(lotId);

            var window = new LotDetailWindow(windowVm)
            {
                Owner = Window.GetWindow(this)
            };

            window.ShowDialog();
        }

        private async void DrawingButton_Click(object sender, RoutedEventArgs e)
        {
            if (_viewModel == null)
            {
                return;
            }

            if (sender is not FrameworkElement element)
            {
                return;
            }

            if (element.DataContext is not ProductDto product)
            {
                return;
            }

            await _viewModel.OpenDrawingAsync(product);
        }
    }
}