using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Printing;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using Mes.Wpf.Modules.InspectionSchedules.ViewModels;

namespace Mes.Wpf.Modules.InspectionSchedules.Views
{
    public partial class InspectionScheduleManagementView : UserControl
    {
        public InspectionScheduleManagementView()
        {
            InitializeComponent();
        }

        private async void RowInspectionDatePicker_OnSelectedDateChanged(object sender, SelectionChangedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not DatePicker datePicker)
            {
                return;
            }

            if (datePicker.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            if (!datePicker.IsKeyboardFocusWithin && !datePicker.IsDropDownOpen)
            {
                return;
            }

            if (e.RemovedItems.Count == 0)
            {
                return;
            }

            DateTime? previousDate = null;
            if (e.RemovedItems.Count > 0 && e.RemovedItems[0] is DateTime removedDate)
            {
                previousDate = removedDate.Date;
            }

            vm.SelectedItem = item;
            await vm.OnInspectionDatePickedAsync(previousDate, datePicker.SelectedDate);
        }

        private async void ReceiveButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.ReceiveAsync();
        }

        private void BundleNoTextBlock_OnMouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not TextBlock textBlock || textBlock.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            if (vm.OpenPlateDataCommand.CanExecute(item))
            {
                vm.OpenPlateDataCommand.Execute(item);
                e.Handled = true;
            }
        }

        private async void InspectionActionButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button)
            {
                return;
            }

            if (button.Tag is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;

            if (item.Status == "RECEIVED")
            {
                await vm.StartAsync();
                return;
            }

            if (item.Status == "IN_PROGRESS")
            {
                await vm.OpenInspectionResultAsync();
            }
        }

        private async void CancelButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.CancelAsync();
        }

        private async void MoveUpButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.MoveUpAsync();
        }

        private async void MoveDownButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.MoveDownAsync();
        }

        private void PrintScheduleButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (vm.Items.Count == 0)
            {
                MessageBox.Show("\uC778\uC1C4\uD560 \uAC80\uC218 \uC2A4\uCF00\uC904\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.", "\uC2A4\uCF00\uC904 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var printDialog = new PrintDialog();
            if (printDialog.PrintTicket != null)
            {
                printDialog.PrintTicket.PageOrientation = PageOrientation.Landscape;
                printDialog.PrintTicket.PageMediaSize = new PageMediaSize(PageMediaSizeName.ISOA4);
            }

            if (printDialog.ShowDialog() != true)
            {
                return;
            }

            if (printDialog.PrintTicket != null)
            {
                printDialog.PrintTicket.PageOrientation = PageOrientation.Landscape;
                printDialog.PrintTicket.PageMediaSize = new PageMediaSize(PageMediaSizeName.ISOA4);
            }

            var document = BuildSchedulePrintDocument(vm.Items.ToList(), vm.SearchDate, vm.TotalShipQty);
            document.PageWidth = printDialog.PrintableAreaWidth;
            document.PageHeight = printDialog.PrintableAreaHeight;
            document.PagePadding = new Thickness(24);
            document.ColumnWidth = printDialog.PrintableAreaWidth;

            printDialog.PrintDocument(((IDocumentPaginatorSource)document).DocumentPaginator, "\uAC80\uC218 \uC2A4\uCF00\uC904");
        }

        private static FlowDocument BuildSchedulePrintDocument(
            IReadOnlyList<InspectionScheduleListItemDto> items,
            DateTime? searchDate,
            int totalShipQty)
        {
            var document = new FlowDocument
            {
                FontFamily = new FontFamily("Malgun Gothic"),
                FontSize = 9,
                PagePadding = new Thickness(24)
            };

            document.Blocks.Add(new Paragraph(new Run("\uAC80\uC218 \uC2A4\uCF00\uC904 \uAD00\uB9AC"))
            {
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0, 0, 0, 4),
                TextAlignment = TextAlignment.Center
            });

            var subTitleText = searchDate.HasValue
                ? $"\uAC80\uC218\uC77C: {searchDate.Value:yyyy-MM-dd}    \uC870\uD68C\uAC74\uC218: {items.Count:N0}    \uCD9C\uACE0\uC218\uB7C9 \uD569\uACC4: {totalShipQty:N0}"
                : $"\uC870\uD68C\uAC74\uC218: {items.Count:N0}    \uCD9C\uACE0\uC218\uB7C9 \uD569\uACC4: {totalShipQty:N0}";

            document.Blocks.Add(new Paragraph(new Run(subTitleText))
            {
                FontSize = 9,
                Margin = new Thickness(0, 0, 0, 8),
                TextAlignment = TextAlignment.Right
            });

            var table = new Table
            {
                CellSpacing = 0,
                BorderBrush = Brushes.Black,
                BorderThickness = new Thickness(0.6)
            };

            foreach (var width in new[] { 72.0, 56.0, 105.0, 150.0, 58.0, 58.0, 68.0, 68.0, 72.0, 58.0, 70.0 })
            {
                table.Columns.Add(new TableColumn { Width = new GridLength(width) });
            }

            var rowGroup = new TableRowGroup();
            table.RowGroups.Add(rowGroup);

            AddScheduleHeaderRow(rowGroup);
            foreach (var item in items)
            {
                AddScheduleDataRow(rowGroup, item);
            }

            document.Blocks.Add(table);
            return document;
        }

        private static void AddScheduleHeaderRow(TableRowGroup rowGroup)
        {
            var row = new TableRow { Background = new SolidColorBrush(Color.FromRgb(243, 244, 246)) };
            rowGroup.Rows.Add(row);

            foreach (var header in new[] { "LOT", "\uBB36\uC74C", "\uACE0\uAC1D\uC0AC", "\uD488\uBAA9\uBA85", "\uBC1C\uC8FC\uC218\uB7C9", "\uCD9C\uACE0\uC218\uB7C9", "\uB0A9\uAE30\uC77C", "\uAC80\uC218\uC77C\uC790", "\uC678\uC8FC\uC0C1\uD0DC", "\uC0C1\uD0DC", "\uB3C4\uBA74" })
            {
                row.Cells.Add(CreateCell(header, true));
            }
        }

        private static void AddScheduleDataRow(TableRowGroup rowGroup, InspectionScheduleListItemDto item)
        {
            var row = new TableRow();
            rowGroup.Rows.Add(row);

            row.Cells.Add(CreateCell(item.LotNo));
            row.Cells.Add(CreateCell(item.BundleNo ?? string.Empty));
            row.Cells.Add(CreateCell(item.PartnerName));
            row.Cells.Add(CreateCell(item.ProductName, false, TextAlignment.Left));
            row.Cells.Add(CreateCell(item.OrderQty.ToString("N0", CultureInfo.InvariantCulture)));
            row.Cells.Add(CreateCell(item.ShipQty.ToString("N0", CultureInfo.InvariantCulture)));
            row.Cells.Add(CreateCell(item.DueDate.ToString("yyyy-MM-dd")));
            row.Cells.Add(CreateCell(item.InspectionDate.ToString("yyyy-MM-dd")));
            row.Cells.Add(CreateCell(item.DiecutStatus ?? string.Empty));
            row.Cells.Add(CreateCell(ToStatusText(item.Status)));
            row.Cells.Add(CreateCell(item.DrawingNo ?? string.Empty));
        }

        private static TableCell CreateCell(string text, bool isHeader = false, TextAlignment alignment = TextAlignment.Center)
        {
            var paragraph = new Paragraph(new Run(text ?? string.Empty))
            {
                Margin = new Thickness(2, 1, 2, 1),
                TextAlignment = alignment,
                LineHeight = 12
            };

            return new TableCell(paragraph)
            {
                BorderBrush = Brushes.Black,
                BorderThickness = new Thickness(0.4),
                Padding = new Thickness(2),
                FontSize = isHeader ? 8.5 : 8,
                FontWeight = isHeader ? FontWeights.Bold : FontWeights.Normal
            };
        }

        private static string ToStatusText(string status)
        {
            return status switch
            {
                "WAITING" => "\uB300\uAE30",
                "RECEIVED" => "\uC785\uACE0\uC644\uB8CC",
                "IN_PROGRESS" => "\uC9C4\uD589\uC911",
                "PARTIAL_DONE" => "\uBD84\uD560\uC644\uB8CC",
                "DONE" => "\uAC80\uC218\uC644\uB8CC",
                "CANCELED" => "\uCDE8\uC18C",
                _ => status
            };
        }
    }
}
