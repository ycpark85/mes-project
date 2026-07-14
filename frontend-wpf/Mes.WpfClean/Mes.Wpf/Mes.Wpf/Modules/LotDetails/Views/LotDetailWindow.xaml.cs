using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Documents;
using System.Windows.Navigation;
using Mes.Wpf.Modules.LotDetails.Dtos;
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

        private async void AttachmentImage_RequestNavigate(object sender, RequestNavigateEventArgs e)
        {
            e.Handled = true;

            if (e.Uri == null || string.IsNullOrWhiteSpace(e.Uri.ToString()))
            {
                return;
            }

            var fileName = GetAttachmentFileName(sender);

            await OpenAttachmentImageFromTempAsync(
                e.Uri.AbsoluteUri,
                fileName);
        }

        private static string? GetAttachmentFileName(object sender)
        {
            if (sender is Hyperlink hyperlink &&
                hyperlink.DataContext is LotTraceInspectionDefectDto defect)
            {
                return defect.FirstAttachment?.FileName;
            }

            return null;
        }

        private static async Task OpenAttachmentImageFromTempAsync(
            string downloadUrl,
            string? fileName)
        {
            using var httpClient = new HttpClient();
            using var response = await httpClient.GetAsync(
                downloadUrl,
                HttpCompletionOption.ResponseHeadersRead);

            response.EnsureSuccessStatusCode();

            var safeFileName = MakeSafeFileName(fileName);

            if (string.IsNullOrWhiteSpace(Path.GetExtension(safeFileName)))
            {
                safeFileName += GetExtensionFromContentType(
                    response.Content.Headers.ContentType?.MediaType);
            }

            if (string.IsNullOrWhiteSpace(Path.GetExtension(safeFileName)))
            {
                safeFileName += ".jpg";
            }

            var tempFolder = Path.Combine(
                Path.GetTempPath(),
                "Mes.Wpf",
                "DefectImages");

            Directory.CreateDirectory(tempFolder);

            var tempFilePath = Path.Combine(
                tempFolder,
                $"{DateTime.Now:yyyyMMddHHmmssfff}_{safeFileName}");

            await using (var source = await response.Content.ReadAsStreamAsync())
            await using (var destination = new FileStream(
                tempFilePath,
                FileMode.CreateNew,
                FileAccess.Write,
                FileShare.None,
                81920,
                FileOptions.Asynchronous | FileOptions.SequentialScan))
            {
                await source.CopyToAsync(destination);
            }

            Process.Start(new ProcessStartInfo
            {
                FileName = tempFilePath,
                UseShellExecute = true
            });
        }

        private static string MakeSafeFileName(string? fileName)
        {
            var value = string.IsNullOrWhiteSpace(fileName)
                ? "defect_image"
                : fileName.Trim();

            foreach (var invalidChar in Path.GetInvalidFileNameChars())
            {
                value = value.Replace(invalidChar, '_');
            }

            return value;
        }

        private static string GetExtensionFromContentType(string? mediaType)
        {
            return mediaType switch
            {
                "image/png" => ".png",
                "image/jpeg" => ".jpg",
                "image/jpg" => ".jpg",
                "image/gif" => ".gif",
                "image/webp" => ".webp",
                "image/bmp" => ".bmp",
                _ => string.Empty
            };
        }

        protected override void OnClosed(EventArgs e)
        {
            _viewModel.RequestClose -= OnRequestClose;
            base.OnClosed(e);
        }
    }
}
