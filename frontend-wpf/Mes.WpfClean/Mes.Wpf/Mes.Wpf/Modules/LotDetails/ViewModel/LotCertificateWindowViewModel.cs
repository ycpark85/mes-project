using System;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.LotDetails.Dtos;

namespace Mes.Wpf.Modules.LotDetails.ViewModels
{
    public class LotCertificateWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private LotTraceDetailDto? _detail;

        private string _productName = "-";
        private string _productSpec = "-";
        private string _inspectionDateText = "-";
        private string _partnerName = "-";
        private int _inspectionTotalQty;
        private string _inspectionTotalQtyText = "-";
        private string _lotNo = "-";
        private string _inspectorName = "-";
        private bool _isPrintedProduct;
        private string _printContentResult = "-";
        private string _appearanceResult = "이상없음";
        private string _printStateResult = "-";
        private string _sampleLetter = "-";
        private string _sampleSizeText = "5";
        private string _acText = "0";
        private string _reText = "1";
        private string _dimensionSample1 = "-";
        private string _dimensionSample2 = "-";
        private string _dimensionSample3 = "-";
        private string _dimensionSample4 = "-";
        private string _dimensionSample5 = "-";
        private string _judgmentText = "P";
        private string _bindingPrintTypeText = "-";

        public LotCertificateWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            CloseCommand = new RelayCommand(_ => RequestClose?.Invoke());
            PrintCommand = new RelayCommand(_ => RequestPrint?.Invoke());
            
        }

        public event Action? RequestClose;
        public event Action? RequestPrint;

        public ICommand CloseCommand { get; }

        public ICommand PrintCommand { get; }

       

        public string CertificateTitle => "최종검사 성적서_Coated Tyvek";

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public LotTraceDetailDto? Detail
        {
            get => _detail;
            set
            {
                if (SetProperty(ref _detail, value))
                {
                    ApplyDetailToDisplay();
                }
            }
        }

        public string ProductName
        {
            get => _productName;
            set => SetProperty(ref _productName, value);
        }

        public string ProductSpec
        {
            get => _productSpec;
            set => SetProperty(ref _productSpec, value);
        }

        public string InspectionDateText
        {
            get => _inspectionDateText;
            set => SetProperty(ref _inspectionDateText, value);
        }

        public string PartnerName
        {
            get => _partnerName;
            set => SetProperty(ref _partnerName, value);
        }

        public int InspectionTotalQty
        {
            get => _inspectionTotalQty;
            set => SetProperty(ref _inspectionTotalQty, value);
        }

        public string InspectionTotalQtyText
        {
            get => _inspectionTotalQtyText;
            set => SetProperty(ref _inspectionTotalQtyText, value);
        }

        public string LotNo
        {
            get => _lotNo;
            set => SetProperty(ref _lotNo, value);
        }

        public string InspectorName
        {
            get => _inspectorName;
            set => SetProperty(ref _inspectorName, value);
        }

        public bool IsPrintedProduct
        {
            get => _isPrintedProduct;
            set => SetProperty(ref _isPrintedProduct, value);
        }

        public string PrintContentResult
        {
            get => _printContentResult;
            set => SetProperty(ref _printContentResult, value);
        }

        public string AppearanceResult
        {
            get => _appearanceResult;
            set => SetProperty(ref _appearanceResult, value);
        }

        public string PrintStateResult
        {
            get => _printStateResult;
            set => SetProperty(ref _printStateResult, value);
        }

        public string SampleLetter
        {
            get => _sampleLetter;
            set => SetProperty(ref _sampleLetter, value);
        }

        public string SampleSizeText
        {
            get => _sampleSizeText;
            set => SetProperty(ref _sampleSizeText, value);
        }

        public string AcText
        {
            get => _acText;
            set => SetProperty(ref _acText, value);
        }

        public string ReText
        {
            get => _reText;
            set => SetProperty(ref _reText, value);
        }

        public string DimensionSample1
        {
            get => _dimensionSample1;
            set => SetProperty(ref _dimensionSample1, value);
        }

        public string DimensionSample2
        {
            get => _dimensionSample2;
            set => SetProperty(ref _dimensionSample2, value);
        }

        public string DimensionSample3
        {
            get => _dimensionSample3;
            set => SetProperty(ref _dimensionSample3, value);
        }

        public string DimensionSample4
        {
            get => _dimensionSample4;
            set => SetProperty(ref _dimensionSample4, value);
        }

        public string DimensionSample5
        {
            get => _dimensionSample5;
            set => SetProperty(ref _dimensionSample5, value);
        }

        public string JudgmentText
        {
            get => _judgmentText;
            set => SetProperty(ref _judgmentText, value);
        }

        public string BindingPrintTypeText
        {
            get => _bindingPrintTypeText;
            set => SetProperty(ref _bindingPrintTypeText, value);
        }

        public async Task InitializeAsync(long lotId)
        {
            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<LotTraceDetailDto>(
                    $"{ApiRoutes.Lots}/{lotId}/detail");

                if (!result.Success || result.Data == null)
                {
                    Detail = null;
                    _messageService.ShowError(result.Message ?? "LOT 성적서 정보를 조회하지 못했습니다.");
                    return;
                }

                Detail = result.Data;
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void ApplyDetailToDisplay()
        {
            ProductName = Detail?.ProductOrder.ProductName ?? "-";
            ProductSpec = Detail?.ProductOrder.ProductSpec ?? "-";
            InspectionDateText = FormatDate(Detail?.Inspection?.InspectionDate);
            PartnerName = Detail?.ProductOrder.PartnerName ?? "-";

            InspectionTotalQty = Detail?.Inspection?.InspectedQty
                                 ?? Detail?.LotBasic.LotQty
                                 ?? 0;

            InspectionTotalQtyText = FormatInt(InspectionTotalQty);
            LotNo = Detail?.LotBasic.LotNo ?? "-";
            InspectorName = Detail?.Inspection?.CreatedBy ?? "-";

            IsPrintedProduct =
                Detail?.OutsourceWorks.Any(x =>
                    string.Equals(x.ProcessType, "PRINT", StringComparison.OrdinalIgnoreCase)) == true;

            PrintContentResult = IsPrintedProduct ? "이상없음" : "-";
            AppearanceResult = "이상없음";
            PrintStateResult = IsPrintedProduct ? "이상없음" : "-";

            SampleLetter = BuildSampleLetter(InspectionTotalQty);
            SampleSizeText = "5";
            AcText = "0";
            ReText = "1";

            DimensionSample1 = ProductSpec;
            DimensionSample2 = ProductSpec;
            DimensionSample3 = ProductSpec;
            DimensionSample4 = ProductSpec;
            DimensionSample5 = ProductSpec;

            JudgmentText = "P";

            BindingPrintTypeText = IsPrintedProduct
                ? "PRINT (인쇄) : 인쇄품 성적서 출력"
                : "CUT (절단) : 무지 성적서 출력";
        }

        private static string BuildSampleLetter(int lotSize)
        {
            if (lotSize <= 0)
            {
                return "-";
            }

            if (lotSize <= 50)
            {
                return "A";
            }

            if (lotSize <= 500)
            {
                return "B";
            }

            if (lotSize <= 35000)
            {
                return "C";
            }

            return "D";
        }

        private static string FormatDate(DateTime? value)
        {
            return value.HasValue ? value.Value.ToString("yyyy-MM-dd") : "-";
        }

        private static string FormatInt(int value)
        {
            return value > 0 ? value.ToString("N0") : "-";
        }
    }
}