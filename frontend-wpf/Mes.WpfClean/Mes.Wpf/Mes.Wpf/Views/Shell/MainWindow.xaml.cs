using Mes.Wpf.Core.Configuration;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Infrastructure.Api;
using Mes.Wpf.Infrastructure.Dialogs;
using Mes.Wpf.Modules.DefectTypes.ViewModels;
using Mes.Wpf.Modules.Drawings.ViewModels;
using Mes.Wpf.Modules.Drawings.Views;
using Mes.Wpf.Modules.Partners.ViewModels;
using Mes.Wpf.Modules.Partners.Views;
using Mes.Wpf.Modules.Processes.ViewModels;
using Mes.Wpf.Modules.Processes.Views;
using Mes.Wpf.Modules.Products.ViewModels;
using Mes.Wpf.Modules.Products.Views;
using Mes.Wpf.Modules.RoutingTemplates.ViewModels;
using Mes.Wpf.Modules.RoutingTemplates.Views;
using Mes.Wpf.Modules.OrderLines.ViewModels;
using Mes.Wpf.Modules.OrderLines.Views;
using Mes.Wpf.Modules.OrderLineList.ViewModels;
using Mes.Wpf.Modules.OrderLineList.Views;

using Mes.Wpf.Modules.Lots.ViewModels;
using Mes.Wpf.Modules.Lots.Views;
using Mes.Wpf.Modules.OrderLineList.Dtos;

using Mes.Wpf.Modules.InspectionSchedules.ViewModels;
using Mes.Wpf.Modules.InspectionSchedules.Views;

using Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Views;
using System.Threading.Tasks;


using System.Windows;

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

        private async void Partner_Click(object sender, RoutedEventArgs e)
        {
            var partnerPage = new PartnerPage();
            var partnerViewModel = new PartnerPageViewModel(_apiClient, _messageService);

            partnerPage.DataContext = partnerViewModel;

            MainContent.Content = partnerPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "거래처 관리";
            HeaderSubtitle.Text = "거래처 마스터 등록 / 조회 / 수정 / 삭제 / 벌크업로드";

            await partnerViewModel.InitializeAsync();
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

        private async void Drawing_Click(object sender, RoutedEventArgs e)
        {
            var drawingPage = new DrawingPage();
            var drawingFileOpener = new DrawingFileOpener(_messageService);

            var drawingViewModel = new DrawingPageViewModel(_apiClient, _messageService, drawingFileOpener);

            drawingPage.DataContext = drawingViewModel;

            MainContent.Content = drawingPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "도면 관리";
            HeaderSubtitle.Text = "도면 / 리비전 / 파일 등록 / 조회 / 수정";

            await drawingViewModel.InitializeAsync();
        }

        private async void Product_Click(object sender, RoutedEventArgs e)
        {
            var productPage = new ProductPage();
            var drawingFileOpener = new DrawingFileOpener(_messageService);
            var drawingViewer = new DrawingViewer(_apiClient, _messageService, drawingFileOpener);

            var productViewModel = new ProductPageViewModel(
                _apiClient,
                _messageService,
                drawingViewer);

            productPage.DataContext = productViewModel;
            MainContent.Content = productPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "품목 관리";
            HeaderSubtitle.Text = "품목 마스터 등록 / 조회 / 수정 / 삭제 / 벌크업로드";

            await productViewModel.InitializeAsync();
        }

        private async void OrderLineCreate_Click(object sender, RoutedEventArgs e)
        {
            var page = new OrderLineCreatePage();
            var drawingFileOpener = new DrawingFileOpener(_messageService);
            var drawingViewer = new DrawingViewer(_apiClient, _messageService, drawingFileOpener);

            var viewModel = new OrderLineCreatePageViewModel(
                _apiClient,
                _messageService,
                drawingViewer);

            page.DataContext = viewModel;
            MainContent.Content = page;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "수주 등록";
            HeaderSubtitle.Text = "수주 헤더 / 수주 라인 등록";

            await viewModel.InitializeAsync();
        }

        private async void OrderLineList_Click(object sender, RoutedEventArgs e)
        {
            await OpenOrderLineListAsync();
        }

        private async Task OpenOrderLineDetailAsync(long orderLineId)
        {
            var page = new OrderLineDetailPage();
            var vm = new OrderLineDetailPageViewModel(
                _apiClient,
                _messageService,
                async () => await OpenOrderLineListAsync()
            );

            page.DataContext = vm;
            MainContent.Content = page;

            await vm.InitializeAsync(orderLineId);
        }

        private async Task OpenOrderLineListAsync()
        {
            var page = new OrderLineListPage();
            var vm = new OrderLineListPageViewModel(
                _apiClient,
                _messageService,
                async orderLineId => await OpenOrderLineDetailAsync(orderLineId),
                async item => await OpenLotCreateWindowAsync(item)
            );

            page.DataContext = vm;
            MainContent.Content = page;
            MainContent.Visibility = Visibility.Visible;
            HeaderTitle.Text = "발주리스트";
            HeaderSubtitle.Text = "수주라인 조회 / 발주상세 / LOT 생성";

            await vm.InitializeAsync();
        }



        private async Task OpenLotCreateWindowAsync(OrderLineListItemDto item)
        {
            var drawingFileOpener = new DrawingFileOpener(_messageService);
            var drawingViewer = new DrawingViewer(_apiClient, _messageService, drawingFileOpener);

            var vm = new LotCreateWindowViewModel(
                _apiClient,
                _messageService,
                drawingViewer,
                drawingFileOpener);

            var window = new LotCreateWindow(vm)
            {
                Owner = this
            };

            await vm.InitializeAsync(item.OrderLineId);
            window.ShowDialog();

            await OpenOrderLineListAsync();
        }

        private async void LotProcess_Click(object sender, RoutedEventArgs e)
        {
            var page = new LotPage();
            var viewModel = new LotPageViewModel(_apiClient, _messageService);

            page.DataContext = viewModel;
            MainContent.Content = page;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "LOT 공정관리";
            HeaderSubtitle.Text = "LOT 조회 / 공정 진행상태 확인 / 외주공정 시작 / 완료";

            await viewModel.InitializeAsync();
        }

        private async void InspectionWorkInstruction_Click(object sender, RoutedEventArgs e)
        {
            var inspectionWorkInstructionPage = new InspectionWorkInstructionPage();
            var inspectionWorkInstructionViewModel = new InspectionWorkInstructionPageViewModel(_apiClient, _messageService);

            inspectionWorkInstructionPage.DataContext = inspectionWorkInstructionViewModel;
            MainContent.Content = inspectionWorkInstructionPage;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "검수 작업지시 / 등록";
            HeaderSubtitle.Text = "최초 검수일정이 등록되지 않은 LOT 기준 검수 작업지시 등록";

            await inspectionWorkInstructionViewModel.InitializeAsync();
        }

        private async void InspectionScheduleManagement_Click(object sender, RoutedEventArgs e)
        {
            var view = new InspectionScheduleManagementView();
            var viewModel = new InspectionScheduleManagementPageViewModel(_apiClient, _messageService);

            view.DataContext = viewModel;
            MainContent.Content = view;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "검수 스케줄 관리";
            HeaderSubtitle.Text = "검수 일정 조회 / 일정변경 / 입고완료 / 검수시작 / 취소 / 순서변경";

            await viewModel.InitializeAsync();
        }


        private async void OutsourceWorkInstruction_Click(object sender, RoutedEventArgs e)
        {
            var page = new OutsourceWorkInstructionPage();
            var viewModel = new OutsourceWorkInstructionPageViewModel(_apiClient, _messageService);

            page.DataContext = viewModel;
            MainContent.Content = page;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "외주 작업지시 등록";
            HeaderSubtitle.Text = "후보 LOT 조회 / 묶음·개별 작업지시 생성 / 파일 첨부 / 일괄 저장";

            await viewModel.InitializeAsync();
        }

        private async void OutsourcePurchaseOrder_Click(object sender, RoutedEventArgs e)
        {
            var page = new OutsourcePurchaseOrderPage();
            var viewModel = new OutsourcePurchaseOrderPageViewModel(_apiClient, _messageService);

            page.DataContext = viewModel;
            MainContent.Content = page;
            MainContent.Visibility = Visibility.Visible;

            HeaderTitle.Text = "외주 발주서 작성 / 출력";
            HeaderSubtitle.Text = "재단 / 인쇄 발주 대상 조회 / 발주서 헤더·상세 입력 / 출력";

            await viewModel.InitializeAsync();
        }


    }
}