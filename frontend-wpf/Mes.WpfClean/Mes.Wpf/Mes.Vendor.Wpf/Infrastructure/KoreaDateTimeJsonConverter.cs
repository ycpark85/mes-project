using System;
using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Mes.Vendor.Wpf.Infrastructure;

public sealed class KoreaDateTimeJsonConverter : JsonConverter<DateTime>
{
    private static readonly TimeZoneInfo KoreaTimeZone =
        TimeZoneInfo.FindSystemTimeZoneById("Korea Standard Time");

    public override DateTime Read(
        ref Utf8JsonReader reader,
        Type typeToConvert,
        JsonSerializerOptions options)
    {
        var raw = reader.GetString()
            ?? throw new JsonException("DateTime value is null.");

        if (HasExplicitOffset(raw)
            && DateTimeOffset.TryParse(
                raw,
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out var instant))
        {
            return TimeZoneInfo.ConvertTime(instant, KoreaTimeZone).DateTime;
        }

        if (DateTime.TryParse(
            raw,
            CultureInfo.InvariantCulture,
            DateTimeStyles.RoundtripKind,
            out var value))
        {
            return value;
        }

        throw new JsonException($"Invalid DateTime value: {raw}");
    }

    public override void Write(
        Utf8JsonWriter writer,
        DateTime value,
        JsonSerializerOptions options)
    {
        writer.WriteStringValue(value);
    }

    private static bool HasExplicitOffset(string value)
    {
        var timeSeparatorIndex = value.IndexOf('T');
        if (timeSeparatorIndex < 0)
        {
            return false;
        }

        var timePart = value[(timeSeparatorIndex + 1)..];
        return timePart.EndsWith("Z", StringComparison.OrdinalIgnoreCase)
            || timePart.Contains('+')
            || timePart.Contains('-');
    }
}
