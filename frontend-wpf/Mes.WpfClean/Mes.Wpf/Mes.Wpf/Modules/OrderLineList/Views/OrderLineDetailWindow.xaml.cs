using System.Windows;

namespace Mes.Wpf.Modules.OrderLineList.Views
{
    public partial class OrderLineDetailWindow : Window
    {
        public OrderLineDetailWindow(OrderLineDetailPage page)
        {
            InitializeComponent();
            DetailContent.Content = page;
        }
    }
}