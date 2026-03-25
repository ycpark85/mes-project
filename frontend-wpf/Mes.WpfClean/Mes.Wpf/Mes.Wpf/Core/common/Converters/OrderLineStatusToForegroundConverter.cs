using System;
using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;

namespace Mes.Wpf.Core.Converters
{
    public class OrderLineStatusToForegroundConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var status = value?.ToString()?.ToUpperInvariant();

            return status switch
            {
                "OPEN" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#64748B")),
                "CLOSED" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#2563EB")),
                "IN_PROGRESS" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#2563EB")),
                "DONE" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#16A34A")),
                "CANCELED" => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#DC2626")),
                _ => new SolidColorBrush((Color)ColorConverter.ConvertFromString("#6B7280"))
            };
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotSupportedException();
        }
    }
}