using System;
using System.Printing;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Mes.Wpf.Modules.LotDetails.ViewModels;

namespace Mes.Wpf.Modules.LotDetails.Views
{
    public partial class LotCertificateWindow : Window
    {
        private readonly LotCertificateWindowViewModel _viewModel;

        public LotCertificateWindow(LotCertificateWindowViewModel viewModel)
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
            PrintCertificateArea();
        }

        private void PrintCertificateArea()
        {
            if (CertificatePrintArea.ActualWidth <= 0 ||
                CertificatePrintArea.ActualHeight <= 0)
            {
                MessageBox.Show(
                    "인쇄할 성적서 영역을 확인할 수 없습니다.",
                    "인쇄",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                return;
            }

            var printDialog = new PrintDialog();

            if (printDialog.PrintTicket != null)
            {
                printDialog.PrintTicket.PageOrientation = PageOrientation.Landscape;
                printDialog.PrintTicket.PageMediaSize =
                    new PageMediaSize(PageMediaSizeName.ISOA4);
            }

            if (printDialog.ShowDialog() != true)
            {
                return;
            }

            if (printDialog.PrintTicket != null)
            {
                printDialog.PrintTicket.PageOrientation = PageOrientation.Landscape;
                printDialog.PrintTicket.PageMediaSize =
                    new PageMediaSize(PageMediaSizeName.ISOA4);
            }

            var capabilities = printDialog.PrintQueue.GetPrintCapabilities(printDialog.PrintTicket);
            var imageableArea = capabilities.PageImageableArea;

            var originX = imageableArea?.OriginWidth ?? 0;
            var originY = imageableArea?.OriginHeight ?? 0;
            var printableWidth = imageableArea?.ExtentWidth ?? printDialog.PrintableAreaWidth;
            var printableHeight = imageableArea?.ExtentHeight ?? printDialog.PrintableAreaHeight;

            var sourceWidth = CertificatePrintArea.ActualWidth;
            var sourceHeight = CertificatePrintArea.ActualHeight;

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
                var brush = new VisualBrush(CertificatePrintArea)
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

            printDialog.PrintVisual(printVisual, "LOT 성적서");
        }

        protected override void OnClosed(EventArgs e)
        {
            _viewModel.RequestClose -= OnRequestClose;
            _viewModel.RequestPrint -= OnRequestPrint;

            base.OnClosed(e);
        }
    }
}