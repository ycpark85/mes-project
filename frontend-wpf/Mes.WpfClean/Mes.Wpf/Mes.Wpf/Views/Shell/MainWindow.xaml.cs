using System.Windows;
using Mes.Wpf.Core.Configuration;
using Mes.Wpf.Infrastructure.Api;
using Mes.Wpf.Infrastructure.Dialogs;
using Mes.Wpf.Modules.DefectTypes.ViewModels;
using Mes.Wpf.Modules.Processes.ViewModels;
using Mes.Wpf.Modules.Processes.Views;
using Mes.Wpf.Modules.RoutingTemplates.ViewModels;
using Mes.Wpf.Modules.RoutingTemplates.Views;

namespace Mes.Wpf.Views.Shell
{
    public partial class MainWindow : Window
    {
        private readonly ApiClient _apiClient;
        private readonly MessageService _messageService;
        private readonly DefectTypePageViewModel _defectTypePageViewModel;
        private readonly RoutingTemplatePageViewModel _routingTemplatePageViewModel;

        public MainWindow()
        {
            InitializeComponent();

            var appSettings = AppSettings.Load();
            _apiClient = new ApiClient(appSettings.Api.BaseUrl);
            _messageService = new MessageService();

            _defectTypePageViewModel = new DefectTypePageViewModel(_apiClient, _messageService);
            _routingTemplatePageViewModel = new RoutingTemplatePageViewModel(_apiClient, _messageService);

            Loaded += MainWindow_Loaded;
        }

        private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            await _defectTypePageViewModel.InitializeAsync();
            ShowDefectType();
        }

        private void Dashboard_Click(object sender, RoutedEventArgs e)
        {
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

            
            MainContent.Content = processPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "공정 관리";
            HeaderSubtitle.Text = "공정 마스터 등록 / 조회 / 수정 / 삭제";

            await processViewModel.InitializeAsync();
        }

        private async void RoutingTemplate_Click(object sender, RoutedEventArgs e)
        {
            var routingTemplatePage = new RoutingTemplatePage();
            var routingTemplateViewModel = new RoutingTemplatePageViewModel(_apiClient, _messageService);

            routingTemplatePage.DataContext = routingTemplateViewModel;

            
            MainContent.Content = routingTemplatePage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "라우팅 템플릿 관리";
            HeaderSubtitle.Text = "라우팅 템플릿 마스터 등록 / 조회 / 수정 / 삭제";

            await routingTemplateViewModel.InitializeAsync();
        }

        private void ShowDefectType()
        {
            var defectTypePage = new Modules.DefectTypes.Views.DefectTypePage();
            defectTypePage.DataContext = _defectTypePageViewModel;

            MainContent.Content = defectTypePage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "불량유형 관리";
            HeaderSubtitle.Text = "불량유형 마스터 등록 / 조회 / 수정 / 삭제";
        }

        private async void RoutingTemplateStep_Click(object sender, RoutedEventArgs e)
        {
            var routingTemplateStepPage = new RoutingTemplateStepPage();
            var routingTemplateStepViewModel = new RoutingTemplateStepPageViewModel(_apiClient, _messageService);

            routingTemplateStepPage.DataContext = routingTemplateStepViewModel;
            MainContent.Content = routingTemplateStepPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "라우팅 Step 관리";
            HeaderSubtitle.Text = "라우팅 템플릿별 Step 등록 / 조회 / 수정 / 삭제";

            await routingTemplateStepViewModel.InitializeAsync();
        }


    }
}