using System.Windows;
using Mes.Wpf.Core.Configuration;
using Mes.Wpf.Infrastructure.Api;
using Mes.Wpf.Infrastructure.Dialogs;
using Mes.Wpf.Modules.DefectTypes.ViewModels;
using Mes.Wpf.Modules.Processes.ViewModels;
using Mes.Wpf.Modules.Processes.Views;

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
            ShowDefectType();
        }

        private void Dashboard_Click(object sender, RoutedEventArgs e)
        {
            DefectTypePageControl.Visibility = Visibility.Collapsed;
            MainContent.Content = null;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "MES 프로그램";
            HeaderSubtitle.Text = "프론트엔드 아키텍처 베이스";
        }

        private void DefectType_Click(object sender, RoutedEventArgs e)
        {
            ShowDefectType();
        }

        private async void Process_Click(object sender, RoutedEventArgs e)
        {
            var processPage = new ProcessPage();
            var processViewModel = new ProcessPageViewModel(_apiClient, _messageService);

            processPage.DataContext = processViewModel;

            DefectTypePageControl.Visibility = Visibility.Collapsed;
            MainContent.Content = processPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "공정 관리";
            HeaderSubtitle.Text = "공정 마스터 등록 / 조회 / 수정 / 삭제";

            await processViewModel.InitializeAsync();
        }

        private void ShowDefectType()
        {
            MainContent.Content = null;
            MainContent.Visibility = Visibility.Collapsed;
            DefectTypePageControl.Visibility = Visibility.Visible;

            HeaderTitle.Text = "불량유형 관리";
            HeaderSubtitle.Text = "불량유형 마스터 등록 / 조회 / 수정 / 삭제";
        }
    }
}