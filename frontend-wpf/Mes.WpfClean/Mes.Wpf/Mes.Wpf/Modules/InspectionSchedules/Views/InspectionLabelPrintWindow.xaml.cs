using System;
using System.Globalization;
using System.Printing;
using System.Windows;
using System.Windows.Media;

namespace Mes.Wpf.Modules.InspectionSchedules.Views
{
    public partial class InspectionLabelPrintWindow : Window
    {
        private const string PrinterName = "TSC TTP-244 Pro";
        private const double LabelWidthMm = 60.6;
        private const double LabelHeightMm = 40.0;
        private readonly bool _requiresManualLotNo;

        public InspectionLabelPrintWindow(string productName, string productSpec, string lotNo, bool requiresManualLotNo)
        {
            InitializeComponent();

            _requiresManualLotNo = requiresManualLotNo;

            ProductNameTextBox.Text = productName;
            ProductSpecTextBox.Text = productSpec;
            LotNoTextBox.Text = requiresManualLotNo ? string.Empty : lotNo;
            LotNoTextBox.IsReadOnly = !requiresManualLotNo;

            if (requiresManualLotNo)
            {
                MessageBox.Show("\uBCC4\uB3C4\uC758 lot\uB97C \uAE30\uC7AC\uD558\uC5EC \uD504\uB9B0\uD2B8\uD574\uC8FC\uC2DC\uAE30 \uBC14\uB78D\uB2C8\uB2E4", "\uB77C\uBCA8 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Information);
                LotNoTextBox.SelectAll();
                LotNoTextBox.Focus();
            }
            else
            {
                QtyTextBox.Focus();
            }
        }

        private void PrintButton_Click(object sender, RoutedEventArgs e)
        {
            var lotNo = (LotNoTextBox.Text ?? string.Empty).Trim();
            if (_requiresManualLotNo && string.IsNullOrWhiteSpace(lotNo))
            {
                MessageBox.Show("LOT\uB97C \uC785\uB825\uD574\uC8FC\uC138\uC694.", "\uB77C\uBCA8 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Warning);
                LotNoTextBox.Focus();
                return;
            }

            var qtyText = (QtyTextBox.Text ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(qtyText))
            {
                MessageBox.Show("\uC218\uB7C9\uC744 \uC785\uB825\uD574\uC8FC\uC138\uC694.", "\uB77C\uBCA8 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Warning);
                QtyTextBox.Focus();
                return;
            }

            if (!int.TryParse((CopiesTextBox.Text ?? string.Empty).Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var copies) ||
                copies <= 0)
            {
                MessageBox.Show("\uC778\uC1C4\uB9E4\uC218\uB294 1 \uC774\uC0C1\uC758 \uC22B\uC790\uB85C \uC785\uB825\uD574\uC8FC\uC138\uC694.", "\uB77C\uBCA8 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Warning);
                CopiesTextBox.Focus();
                return;
            }

            try
            {
                PrintLabels(
                    ProductNameTextBox.Text.Trim(),
                    ProductSpecTextBox.Text.Trim(),
                    lotNo,
                    BuildQtyText(qtyText),
                    copies);

                MessageBox.Show("\uB77C\uBCA8 \uC778\uC1C4 \uC694\uCCAD\uC774 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.", "\uB77C\uBCA8 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Information);
                DialogResult = true;
                Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"\uB77C\uBCA8 \uC778\uC1C4 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4.\n{ex.Message}", "\uB77C\uBCA8 \uC778\uC1C4", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private static string BuildQtyText(string qtyText)
        {
            return qtyText.EndsWith("EA", StringComparison.OrdinalIgnoreCase)
                ? qtyText
                : $"{qtyText}EA";
        }

        private static void PrintLabels(string productName, string productSpec, string lotNo, string qtyText, int copies)
        {
            using var printServer = new LocalPrintServer();
            using var printQueue = printServer.GetPrintQueue(PrinterName);

            var ticket = printQueue.DefaultPrintTicket;
            ticket.PageMediaSize = new PageMediaSize(MmToDip(LabelWidthMm), MmToDip(LabelHeightMm));
            ticket.PageOrientation = PageOrientation.Portrait;
            ticket.CopyCount = copies;

            var visual = BuildLabelVisual(productName, productSpec, lotNo, qtyText);
            printQueue.UserPrintTicket = ticket;

            var writer = PrintQueue.CreateXpsDocumentWriter(printQueue);
            writer.Write(visual, ticket);
        }

        private static DrawingVisual BuildLabelVisual(string productName, string productSpec, string lotNo, string qtyText)
        {
            var width = MmToDip(LabelWidthMm);
            var height = MmToDip(LabelHeightMm);

            var visual = new DrawingVisual();
            using var context = visual.RenderOpen();

            context.DrawRectangle(Brushes.White, null, new Rect(0, 0, width, height));

            var left = MmToDip(1.8);
            var top = MmToDip(1.9);
            var tableWidth = width - left - MmToDip(2.4);
            var tableHeight = height - top - MmToDip(1.9);
            var labelColumnWidth = MmToDip(17.0);
            var rowHeight = tableHeight / 4.0;

            var blackPen = new Pen(Brushes.Black, 1.6);
            var borderPen = new Pen(Brushes.Black, 2.0);

            context.DrawRoundedRectangle(
                Brushes.White,
                borderPen,
                new Rect(left, top, tableWidth, tableHeight),
                MmToDip(1.4),
                MmToDip(1.4));

            context.DrawLine(blackPen, new Point(left + labelColumnWidth, top), new Point(left + labelColumnWidth, top + tableHeight));
            for (var i = 1; i < 4; i++)
            {
                var y = top + (rowHeight * i);
                context.DrawLine(blackPen, new Point(left, y), new Point(left + tableWidth, y));
            }

            var labelTypeface = new Typeface(new FontFamily("Malgun Gothic"), FontStyles.Normal, FontWeights.Bold, FontStretches.Normal);
            var productNameTypeface = new Typeface(new FontFamily("Malgun Gothic"), FontStyles.Normal, FontWeights.Normal, FontStretches.Normal);
            var valueTypeface = new Typeface(new FontFamily("Arial"), FontStyles.Normal, FontWeights.Normal, FontStretches.Condensed);
            const double labelFontSize = 17;

            DrawFittedText(context, "\uC81C\uD488\uBA85", labelTypeface, labelFontSize, labelFontSize, new Rect(left + 2, top + 1, labelColumnWidth - 4, rowHeight - 2), 1);
            DrawFittedText(context, "\uADDC\uACA9", labelTypeface, labelFontSize, labelFontSize, new Rect(left + 2, top + rowHeight + 1, labelColumnWidth - 4, rowHeight - 2), 1);
            DrawFittedText(context, "LOT", labelTypeface, labelFontSize, labelFontSize, new Rect(left + 2, top + (rowHeight * 2) + 1, labelColumnWidth - 4, rowHeight - 2), 1);
            DrawFittedText(context, "\uC218\uB7C9", labelTypeface, labelFontSize, labelFontSize, new Rect(left + 2, top + (rowHeight * 3) + 1, labelColumnWidth - 4, rowHeight - 2), 1);

            var valueLeft = left + labelColumnWidth;
            var valueWidth = tableWidth - labelColumnWidth;
            var productNamePadding = MmToDip(2.4);
            DrawProductNameText(context, productName, productNameTypeface, 18, 7, new Rect(valueLeft + productNamePadding, top + 1, valueWidth - (productNamePadding * 2), rowHeight - 2));
            DrawFittedText(context, productSpec, valueTypeface, 22, 11, new Rect(valueLeft + 4, top + rowHeight + 1, valueWidth - 8, rowHeight - 2), 1);
            DrawFittedText(context, lotNo, valueTypeface, 22, 13, new Rect(valueLeft + 4, top + (rowHeight * 2) + 1, valueWidth - 8, rowHeight - 2), 1);
            DrawFittedText(context, qtyText, valueTypeface, 22, 13, new Rect(valueLeft + 4, top + (rowHeight * 3) + 1, valueWidth - 8, rowHeight - 2), 1);

            return visual;
        }

        private static void DrawProductNameText(DrawingContext context, string text, Typeface typeface, double maxFontSize, double minFontSize, Rect bounds)
        {
            var value = string.IsNullOrWhiteSpace(text) ? "-" : text.Trim();
            context.PushClip(new RectangleGeometry(bounds));

            for (var fontSize = maxFontSize; fontSize >= minFontSize; fontSize -= 0.5)
            {
                var lines = WrapTextByCharacter(value, typeface, fontSize, bounds.Width, 2);
                if (lines.Count > 2)
                {
                    continue;
                }

                var formattedLines = new FormattedText[lines.Count];
                var totalHeight = 0.0;
                var fits = true;

                for (var i = 0; i < lines.Count; i++)
                {
                    var formatted = CreateFormattedText(lines[i], typeface, fontSize, TextAlignment.Center);
                    formatted.MaxTextWidth = bounds.Width;
                    if (formatted.Width > bounds.Width)
                    {
                        fits = false;
                        break;
                    }

                    formattedLines[i] = formatted;
                    totalHeight += formatted.Height;
                }

                if (!fits || totalHeight > bounds.Height)
                {
                    continue;
                }

                var y = bounds.Top + ((bounds.Height - totalHeight) / 2.0);
                foreach (var formatted in formattedLines)
                {
                    context.DrawText(formatted, new Point(bounds.Left, y));
                    y += formatted.Height;
                }

                context.Pop();
                return;
            }

            var fallback = CreateFormattedText(value, typeface, minFontSize, TextAlignment.Center);
            fallback.MaxTextWidth = bounds.Width;
            fallback.MaxTextHeight = bounds.Height;
            fallback.Trimming = TextTrimming.CharacterEllipsis;
            DrawTextAtCenter(context, fallback, bounds);
            context.Pop();
        }

        private static System.Collections.Generic.List<string> WrapTextByCharacter(string text, Typeface typeface, double fontSize, double maxWidth, int maxLines)
        {
            var lines = new System.Collections.Generic.List<string>();
            var current = string.Empty;

            foreach (var ch in text)
            {
                var candidate = current + ch;
                var formatted = CreateFormattedText(candidate, typeface, fontSize, TextAlignment.Center);

                if (current.Length == 0 || formatted.WidthIncludingTrailingWhitespace <= maxWidth)
                {
                    current = candidate;
                    continue;
                }

                lines.Add(current);
                current = ch.ToString();

                if (lines.Count > maxLines)
                {
                    return lines;
                }
            }

            if (current.Length > 0)
            {
                lines.Add(current);
            }

            return lines;
        }

        private static void DrawFittedText(DrawingContext context, string text, Typeface typeface, double maxFontSize, double minFontSize, Rect bounds, int maxLines)
        {
            var value = string.IsNullOrWhiteSpace(text) ? "-" : text.Trim();

            for (var fontSize = maxFontSize; fontSize >= minFontSize; fontSize -= 0.5)
            {
                var formatted = CreateFormattedText(value, typeface, fontSize, TextAlignment.Center);
                formatted.MaxTextWidth = bounds.Width;
                formatted.MaxTextHeight = bounds.Height;
                formatted.Trimming = TextTrimming.None;

                if (formatted.Height <= bounds.Height && EstimateLineCount(formatted, fontSize) <= maxLines)
                {
                    DrawTextAtCenter(context, formatted, bounds);
                    return;
                }
            }

            var fallback = CreateFormattedText(value, typeface, minFontSize, TextAlignment.Center);
            fallback.MaxTextWidth = bounds.Width;
            fallback.MaxTextHeight = bounds.Height;
            fallback.Trimming = TextTrimming.CharacterEllipsis;
            DrawTextAtCenter(context, fallback, bounds);
        }

        private static int EstimateLineCount(FormattedText text, double fontSize)
        {
            var lineHeight = Math.Max(fontSize * 1.15, 1);
            return Math.Max(1, (int)Math.Ceiling(text.Height / lineHeight));
        }

        private static void DrawTextAtCenter(DrawingContext context, FormattedText formatted, Rect bounds)
        {
            var point = new Point(
                bounds.Left,
                bounds.Top + Math.Max(0, (bounds.Height - formatted.Height) / 2.0));
            context.DrawText(formatted, point);
        }

        private static FormattedText CreateFormattedText(string text, Typeface typeface, double fontSize, TextAlignment alignment)
        {
            return new FormattedText(
                text,
                CultureInfo.GetCultureInfo("ko-KR"),
                FlowDirection.LeftToRight,
                typeface,
                fontSize,
                Brushes.Black,
                VisualTreeHelper.GetDpi(Application.Current.MainWindow).PixelsPerDip)
            {
                TextAlignment = alignment
            };
        }

        private static double MmToDip(double mm)
        {
            return mm * 96.0 / 25.4;
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
