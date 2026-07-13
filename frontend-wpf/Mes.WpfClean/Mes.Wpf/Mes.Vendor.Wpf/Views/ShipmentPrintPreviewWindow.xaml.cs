using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Printing;

namespace Mes.Vendor.Wpf.Views;

public partial class ShipmentPrintPreviewWindow : Window
{
    private readonly FlowDocument _document;

    public ShipmentPrintPreviewWindow(FlowDocument document)
    {
        InitializeComponent();

        _document = document;
        PreviewDocumentReader.Document = _document;
    }

    private void Print_Click(object sender, RoutedEventArgs e)
    {
        var printDialog = new PrintDialog();

        printDialog.PrintTicket.PageOrientation = PageOrientation.Landscape;

        if (printDialog.ShowDialog() != true)
        {
            return;
        }

        printDialog.PrintTicket.PageOrientation = PageOrientation.Landscape;

        _document.PageWidth = printDialog.PrintableAreaWidth;
        _document.PageHeight = printDialog.PrintableAreaHeight;
        _document.PagePadding = new Thickness(24);
        _document.ColumnWidth = printDialog.PrintableAreaWidth - 48;

        printDialog.PrintDocument(
            ((IDocumentPaginatorSource)_document).DocumentPaginator,
            "보현문화 출고리스트");
    }

    private void Close_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
