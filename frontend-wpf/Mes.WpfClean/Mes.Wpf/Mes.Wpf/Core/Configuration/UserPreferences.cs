using System;
using System.IO;
using System.Text.Json;

namespace Mes.Wpf.Core.Configuration
{
    public class UserPreferences
    {
        private const string DirectoryName = "Mes.Wpf";
        private const string FileName = "user-preferences.json";

        public string? SavedLoginId { get; set; }

        public static UserPreferences Load()
        {
            var filePath = GetFilePath();

            if (!File.Exists(filePath))
            {
                return new UserPreferences();
            }

            try
            {
                var json = File.ReadAllText(filePath);
                return JsonSerializer.Deserialize<UserPreferences>(
                    json,
                    new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    }) ?? new UserPreferences();
            }
            catch (IOException)
            {
                return new UserPreferences();
            }
            catch (UnauthorizedAccessException)
            {
                return new UserPreferences();
            }
            catch (JsonException)
            {
                return new UserPreferences();
            }
        }

        public void Save()
        {
            var filePath = GetFilePath();
            var directoryPath = Path.GetDirectoryName(filePath);

            if (!string.IsNullOrWhiteSpace(directoryPath))
            {
                Directory.CreateDirectory(directoryPath);
            }

            var json = JsonSerializer.Serialize(
                this,
                new JsonSerializerOptions
                {
                    WriteIndented = true
                });

            File.WriteAllText(filePath, json);
        }

        private static string GetFilePath()
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            return Path.Combine(localAppData, DirectoryName, FileName);
        }
    }
}
