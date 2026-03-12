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
            var filePath = Path.Combine(AppContext.BaseDirectory, "appsettings.json");

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
                throw new InvalidOperationException("appsettings.json 로드에 실패했습니다.");
            }

            if (settings.Api == null || string.IsNullOrWhiteSpace(settings.Api.BaseUrl))
            {
                throw new InvalidOperationException("Api:BaseUrl 설정이 비어 있습니다.");
            }

            return settings;
        }
    }

    public class ApiSettings
    {
        public string BaseUrl { get; set; } = string.Empty;
    }
}