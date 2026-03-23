using System;
using System.Globalization;
using System.Windows.Data;

namespace Mes.Wpf.Core.Converters
{
    public class IntThousandsConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null)
                return string.Empty;

            if (value is int intValue)
                return intValue.ToString("N0", culture);

            if (int.TryParse(value.ToString(), out var parsed))
                return parsed.ToString("N0", culture);

            return value.ToString() ?? string.Empty;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var text = value?.ToString()?.Replace(",", "").Trim();

            if (string.IsNullOrWhiteSpace(text))
                return 0;

            if (int.TryParse(text, NumberStyles.Integer, culture, out var parsed))
                return parsed;

            return 0;
        }
    }
}