using Mes.Wpf.Core.Interfaces;
using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;

namespace Mes.Wpf.Infrastructure.Api
{
    public class DrawingFileOpener : IDrawingFileOpener
    {
        private readonly IMessageService _messageService;

        public DrawingFileOpener(IMessageService messageService)
        {
            _messageService = messageService;
        }

        public async Task OpenRevisionFileAsync(string downloadUrl, string? fileName)
        {
            try
            {
                using var httpClient = new HttpClient();
                using var response = await httpClient.GetAsync(downloadUrl);
                response.EnsureSuccessStatusCode();

                var bytes = await response.Content.ReadAsByteArrayAsync();

                var safeFileName = string.IsNullOrWhiteSpace(fileName)
                    ? $"drawing_file_{DateTime.Now:yyyyMMddHHmmss}"
                    : fileName;

                var extension = Path.GetExtension(safeFileName);
                if (string.IsNullOrWhiteSpace(extension))
                {
                    var mediaType = response.Content.Headers.ContentType?.MediaType ?? string.Empty;

                    extension = mediaType switch
                    {
                        "application/pdf" => ".pdf",
                        "image/png" => ".png",
                        "image/jpeg" => ".jpg",
                        "image/jpg" => ".jpg",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" => ".xlsx",
                        "application/vnd.ms-excel" => ".xls",
                        "application/msword" => ".doc",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document" => ".docx",
                        _ => string.Empty
                    };

                    safeFileName += extension;
                }

                var tempFolder = Path.Combine(Path.GetTempPath(), "Mes.Wpf", "Drawings");
                Directory.CreateDirectory(tempFolder);

                var tempFilePath = Path.Combine(tempFolder, safeFileName);
                await File.WriteAllBytesAsync(tempFilePath, bytes);

                Process.Start(new ProcessStartInfo
                {
                    FileName = tempFilePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                _messageService.ShowError($"파일 열기 중 오류가 발생했습니다.\n{ex.Message}");
            }
        }
    }
}