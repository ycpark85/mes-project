using System.Windows;
using Mes.Wpf.Core.Configuration;
using Mes.Wpf.Infrastructure.Api;
using Mes.Wpf.Infrastructure.Dialogs;
using Mes.Wpf.Modules.DefectTypes.ViewModels;

namespace Mes.Wpf.Views.Shell
{
    public partial class MainWindow : Window
    {
        private readonly ApiClient _apiClient;
        private readonly MessageService _messageService;
        private readonly DefectTypePageViewModel _defectTypePageViewModel;

        public MainWindow()
        {
            InitializeComponent();

            var appSettings = AppSettings.Load();

            _apiClient = new ApiClient(appSettings.Api.BaseUrl);
            _messageService = new MessageService();
            _defectTypePageViewModel = new DefectTypePageViewModel(_apiClient, _messageService);

            DefectTypePageControl.DataContext = _defectTypePageViewModel;

            Loaded += MainWindow_Loaded;
        }

        private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            await _defectTypePageViewModel.InitializeAsync();
        }
    }
}