using System;
using System.IO;
using System.Text.Json;

namespace Mes.Wpf.Core.Configuration
{
    public class AppSettings
    {
        public ApiSettings Api { get; set; } = new();

        public static AppSettings Load()
        {
#if DEBUG
            const string environment = "Development";
#else
            const string environment = "Production";
#endif

            var baseDirectory = AppContext.BaseDirectory;
            var environmentFilePath = Path.Combine(baseDirectory, $"appsettings.{environment}.json");
            var fallbackFilePath = Path.Combine(baseDirectory, "appsettings.json");

            var filePath = File.Exists(environmentFilePath)
                ? environmentFilePath
                : fallbackFilePath;

            if (!File.Exists(filePath))
            {
                throw new FileNotFoundException($"설정 파일을 찾을 수 없습니다: {filePath}");
            }

            var json = File.ReadAllText(filePath);

            var settings = JsonSerializer.Deserialize<AppSettings>(
                json,
                new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

            if (settings == null)
            {
                throw new InvalidOperationException($"{Path.GetFileName(filePath)} 로드에 실패했습니다.");
            }

            if (settings.Api == null || string.IsNullOrWhiteSpace(settings.Api.BaseUrl))
            {
                throw new InvalidOperationException($"{Path.GetFileName(filePath)}의 Api:BaseUrl 설정이 비어 있습니다.");
            }

            return settings;
        }
    }

    public class ApiSettings
    {
        public string BaseUrl { get; set; } = string.Empty;
    }
}