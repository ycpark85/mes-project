using System;
using System.IO;
using System.Text.Json;

namespace Mes.Vendor.Wpf.Infrastructure;

public sealed class AppSettings
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
        var environmentPath = Path.Combine(baseDirectory, $"appsettings.{environment}.json");
        var fallbackPath = Path.Combine(baseDirectory, "appsettings.json");
        var path = File.Exists(environmentPath) ? environmentPath : fallbackPath;

        if (!File.Exists(path))
        {
            throw new FileNotFoundException($"설정 파일을 찾을 수 없습니다: {path}");
        }

        var settings = JsonSerializer.Deserialize<AppSettings>(
            File.ReadAllText(path),
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

        if (settings == null || string.IsNullOrWhiteSpace(settings.Api.BaseUrl))
        {
            throw new InvalidOperationException("Api:BaseUrl 설정이 비어 있습니다.");
        }

        return settings;
    }
}

public sealed class ApiSettings
{
    public string BaseUrl { get; set; } = string.Empty;
}
