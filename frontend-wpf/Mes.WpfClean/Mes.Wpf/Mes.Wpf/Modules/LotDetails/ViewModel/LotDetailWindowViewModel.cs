using System;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Windows.Input;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.LotDetails.Dtos;

namespace Mes.Wpf.Modules.LotDetails.ViewModels
{
    public class LotDetailWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private LotTraceDetailDto? _detail;

        public LotDetailWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            OutsourceWorks = new ObservableCollection<LotTraceOutsourceWorkDto>();
            Defects = new ObservableCollection<LotTraceInspectionDefectDto>();

            CloseCommand = new RelayCommand(_ => RequestClose?.Invoke());
        }

        public event Action? RequestClose;

        public ObservableCollection<LotTraceOutsourceWorkDto> OutsourceWorks { get; }

        public ObservableCollection<LotTraceInspectionDefectDto> Defects { get; }

        public ICommand CloseCommand { get; }

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
                    RaiseAllDisplayProperties();
                }
            }
        }

        public string LotNo => Detail?.LotBasic.LotNo ?? "-";
        public string LotStatus => Detail?.LotBasic.Status ?? "-";
        public string ReworkText => Detail?.LotBasic.IsRework == true ? "재작업" : "일반";
        public string ParentLotNo => Detail?.LotBasic.ParentLotNo ?? "-";
        public string LotQtyText => FormatInt(Detail?.LotBasic.LotQty);
        public string CreatedDateText => FormatDate(Detail?.LotBasic.CreatedDate);
        public string DueDateText => FormatDate(Detail?.LotBasic.DueDate);

        public string PartnerName => Detail?.ProductOrder.PartnerName ?? "-";
        public string ProductCode => Detail?.ProductOrder.ProductCode ?? "-";
        public string ProductName => Detail?.ProductOrder.ProductName ?? "-";
        public string ProductSpec => Detail?.ProductOrder.ProductSpec ?? "-";
        public string PlateSize => BuildPlateSize();
        public string OrderQtyText => FormatInt(Detail?.ProductOrder.OrderQty);
        public string OrderDueDateText => FormatDate(Detail?.ProductOrder.DueDate);

        public string InspectionStatusText
        {
            get
            {
                if (Detail?.Inspection == null)
                {
                    return "검수일정 없음";
                }

                if (Detail.Inspection.InspectionResultId.HasValue)
                {
                    return "검수완료";
                }

                return Detail.Inspection.ScheduleStatus ?? "검수 전";
            }
        }

        public string InspectionDateText => FormatDate(Detail?.Inspection?.InspectionDate);
        public string InspectedQtyText => FormatNullableInt(Detail?.Inspection?.InspectedQty);
        public string GoodQtyText => FormatNullableInt(Detail?.Inspection?.GoodQty);
        public string DefectQtyText => FormatNullableInt(Detail?.Inspection?.DefectQty);
        public string DefectShipQtyText => FormatNullableInt(Detail?.Inspection?.DefectShipQty);
        public string InspectionResultCreatedAtText => FormatDateTime(Detail?.Inspection?.ResultCreatedAt);

        public bool IsLotCreated => Detail?.Progress.LotCreated == true;
        public bool IsOutsourceInstructionCreated => Detail?.Progress.OutsourceInstructionCreated == true;
        public bool IsOutsourceWorkDone => Detail?.Progress.OutsourceWorkDone == true;
        public bool IsInspectionDone => Detail?.Progress.InspectionDone == true;

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
                    OutsourceWorks.Clear();
                    Defects.Clear();
                    _messageService.ShowError(result.Message ?? "LOT 상세정보 조회에 실패했습니다.");
                    return;
                }

                Detail = result.Data;

                OutsourceWorks.Clear();
                foreach (var item in result.Data.OutsourceWorks)
                {
                    OutsourceWorks.Add(item);
                }

                Defects.Clear();
                if (result.Data.Inspection != null)
                {
                    foreach (var defect in result.Data.Inspection.Defects)
                    {
                        Defects.Add(defect);
                    }
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildPlateSize()
        {
            var width = Detail?.ProductOrder.PanelWidthMm;
            var length = Detail?.ProductOrder.PanelLengthMm;

            if (!width.HasValue && !length.HasValue)
            {
                return "-";
            }

            return $"{width?.ToString() ?? "-"} x {length?.ToString() ?? "-"}";
        }

        private static string FormatDate(DateTime? value)
        {
            return value.HasValue ? value.Value.ToString("yyyy-MM-dd") : "-";
        }

        private static string FormatDateTime(DateTime? value)
        {
            return value.HasValue ? value.Value.ToString("yyyy-MM-dd HH:mm") : "-";
        }

        private static string FormatInt(int? value)
        {
            return value.HasValue ? value.Value.ToString("N0") : "-";
        }

        private static string FormatNullableInt(int? value)
        {
            return value.HasValue ? value.Value.ToString("N0") : "-";
        }

        private void RaiseAllDisplayProperties()
        {
            OnPropertyChanged(nameof(LotNo));
            OnPropertyChanged(nameof(LotStatus));
            OnPropertyChanged(nameof(ReworkText));
            OnPropertyChanged(nameof(ParentLotNo));
            OnPropertyChanged(nameof(LotQtyText));
            OnPropertyChanged(nameof(CreatedDateText));
            OnPropertyChanged(nameof(DueDateText));

            OnPropertyChanged(nameof(PartnerName));
            OnPropertyChanged(nameof(ProductCode));
            OnPropertyChanged(nameof(ProductName));
            OnPropertyChanged(nameof(ProductSpec));
            OnPropertyChanged(nameof(PlateSize));
            OnPropertyChanged(nameof(OrderQtyText));
            OnPropertyChanged(nameof(OrderDueDateText));

            OnPropertyChanged(nameof(InspectionStatusText));
            OnPropertyChanged(nameof(InspectionDateText));
            OnPropertyChanged(nameof(InspectedQtyText));
            OnPropertyChanged(nameof(GoodQtyText));
            OnPropertyChanged(nameof(DefectQtyText));
            OnPropertyChanged(nameof(DefectShipQtyText));
            OnPropertyChanged(nameof(InspectionResultCreatedAtText));

            OnPropertyChanged(nameof(IsLotCreated));
            OnPropertyChanged(nameof(IsOutsourceInstructionCreated));
            OnPropertyChanged(nameof(IsOutsourceWorkDone));
            OnPropertyChanged(nameof(IsInspectionDone));
        }
    }
}