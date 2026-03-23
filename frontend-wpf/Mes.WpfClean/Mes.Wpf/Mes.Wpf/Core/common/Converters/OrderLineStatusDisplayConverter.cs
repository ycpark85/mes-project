using System;
using System.Globalization;
using System.Windows.Data;

namespace Mes.Wpf.Core.Converters
{
    public class OrderLineStatusDisplayConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var status = value?.ToString()?.ToUpperInvariant();

            return status switch
            {
                "CLOSED" => "IN_PROGRESS",
                _ => status ?? string.Empty
            };
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var status = value?.ToString()?.ToUpperInvariant();

            return status switch
            {
                "IN_PROGRESS" => "CLOSED",
                _ => status ?? string.Empty
            };
        }
    }
}