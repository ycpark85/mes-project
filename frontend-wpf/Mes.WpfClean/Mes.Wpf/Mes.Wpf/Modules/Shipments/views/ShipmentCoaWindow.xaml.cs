using Mes.Wpf.Modules.Shipments.ViewModels;
using System;
using System.Printing;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Mes.Wpf.Modules.Shipments.Views
{
    public partial class ShipmentCoaWindow : Window
    {
        private readonly ShipmentCoaWindowViewModel _viewModel;

        public ShipmentCoaWindow(ShipmentCoaWindowViewModel viewModel)
        {
            InitializeComponent();

            _viewModel = viewModel;
            DataContext = _viewModel;

            _viewModel.RequestClose += OnRequestClose;
            _viewModel.RequestPrint += OnRequestPrint;
        }

        private void OnRequestClose()
        {
            Close();
        }

        private void OnRequestPrint()
        {
            PrintCoaArea();
        }

        private void PrintCoaArea()
        {
            if (CoaPrintArea.ActualWidth <= 0 || CoaPrintArea.ActualHeight <= 0)
            {
                return;
            }

            var printDialog = new PrintDialog();

            if (printDialog.PrintTicket != null)
            {
                printDialog.PrintTicket.PageOrientation = PageOrientation.Portrait;
                printDialog.PrintTicket.PageMediaSize = new PageMediaSize(PageMediaSizeName.ISOA4);
            }

            if (printDialog.ShowDialog() != true)
            {
                return;
            }

            if (printDialog.PrintTicket != null)
            {
                printDialog.PrintTicket.PageOrientation = PageOrientation.Portrait;
                printDialog.PrintTicket.PageMediaSize = new PageMediaSize(PageMediaSizeName.ISOA4);
            }

            var capabilities = printDialog.PrintQueue.GetPrintCapabilities(printDialog.PrintTicket);
            var imageableArea = capabilities.PageImageableArea;

            var originX = imageableArea?.OriginWidth ?? 0;
            var originY = imageableArea?.OriginHeight ?? 0;
            var printableWidth = imageableArea?.ExtentWidth ?? printDialog.PrintableAreaWidth;
            var printableHeight = imageableArea?.ExtentHeight ?? printDialog.PrintableAreaHeight;

            var sourceWidth = CoaPrintArea.ActualWidth;
            var sourceHeight = CoaPrintArea.ActualHeight;

            var scale = Math.Min(
                printableWidth / sourceWidth,
                printableHeight / sourceHeight);

            var scaledWidth = sourceWidth * scale;
            var scaledHeight = sourceHeight * scale;

            var offsetX = originX + ((printableWidth - scaledWidth) / 2);
            var offsetY = originY + ((printableHeight - scaledHeight) / 2);

            var printVisual = new DrawingVisual();

            using (var context = printVisual.RenderOpen())
            {
                var brush = new VisualBrush(CoaPrintArea)
                {
                    Stretch = Stretch.Fill
                };

                context.PushTransform(new TranslateTransform(offsetX, offsetY));
                context.PushTransform(new ScaleTransform(scale, scale));
                context.DrawRectangle(
                    brush,
                    null,
                    new Rect(0, 0, sourceWidth, sourceHeight));
                context.Pop();
                context.Pop();
            }

            printDialog.PrintVisual(printVisual, "COA");
        }

        protected override void OnClosed(EventArgs e)
        {
            _viewModel.RequestClose -= OnRequestClose;
            _viewModel.RequestPrint -= OnRequestPrint;

            base.OnClosed(e);
        }
    }
}