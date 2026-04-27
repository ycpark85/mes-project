using System.Windows;
using Mes.Wpf.Modules.BohyunOutsourceManagement.ViewModels;

namespace Mes.Wpf.Modules.BohyunOutsourceManagement.Views
{
    public partial class BohyunOutsourceWorkDoneWindow : Window
    {
        public BohyunOutsourceWorkDoneWindow(BohyunOutsourceWorkDoneWindowViewModel viewModel)
        {
            InitializeComponent();

            DataContext = viewModel;
            viewModel.OwnerWindow = this;
        }
    }
}