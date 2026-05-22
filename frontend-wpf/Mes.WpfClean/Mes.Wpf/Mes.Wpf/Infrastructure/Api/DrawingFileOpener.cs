using Mes.Wpf.Core.Interfaces;
using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Infrastructure.Api
{
    public class DrawingFileOpener : IDrawingFileOpener
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        public DrawingFileOpener(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;
        }

        public async Task OpenRevisionFileAsync(string downloadUrl, string? fileName)
        {
            try
            {
                var bytes = await _apiClient.GetBytesAsync(downloadUrl);

                if (bytes == null || bytes.Length == 0)
                {
                    _messageService.ShowError(
                        "도면 파일을 다운로드할 수 없습니다.\n로그인 권한 또는 도면 파일 정보를 확인하세요.");
                    return;
                }

                var safeFileName = BuildSafeFileName(fileName);

                var tempFolder = Path.Combine(
                    Path.GetTempPath(),
                    "Mes.Wpf",
                    "Drawings");

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

        private static string BuildSafeFileName(string? fileName)
        {
            var name = string.IsNullOrWhiteSpace(fileName)
                ? $"drawing_file_{DateTime.Now:yyyyMMddHHmmss}"
                : fileName.Trim();

            foreach (var invalidChar in Path.GetInvalidFileNameChars())
            {
                name = name.Replace(invalidChar, '_');
            }

            name = name
                .Replace("/", "_")
                .Replace("\\", "_")
                .Trim();

            if (string.IsNullOrWhiteSpace(name) || name == "." || name == "..")
            {
                name = $"drawing_file_{DateTime.Now:yyyyMMddHHmmss}";
            }

            if (string.IsNullOrWhiteSpace(Path.GetExtension(name)))
            {
                name += ".bin";
            }

            var extension = Path.GetExtension(name);
            var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(name);

            if (fileNameWithoutExtension.Length > 120)
            {
                fileNameWithoutExtension = fileNameWithoutExtension.Substring(0, 120);
            }

            return $"{fileNameWithoutExtension}{extension}";
        }
    }
}