using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Dashboard.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Input;

namespace Mes.Wpf.Modules.Dashboard.ViewModels
{
    public class DashboardPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private DateTime _fromDate;
        private DateTime _toDate;
        private DashboardSummaryDto? _summary;

        public DashboardPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            var today = DateTime.Today;

            FromDate = new DateTime(today.Year, today.Month, 1);
            ToDate = today;

            KpiCards = new ObservableCollection<DashboardKpiCardItemViewModel>();
            OutsourceSegments = new ObservableCollection<DashboardStatusSegmentItemViewModel>();
            InspectionSegments = new ObservableCollection<DashboardStatusSegmentItemViewModel>();
            FlowSteps = new ObservableCollection<DashboardFlowStepItemViewModel>();
            Alerts = new ObservableCollection<DashboardAlertItemViewModel>();
            QualityMetrics = new ObservableCollection<DashboardQualityMetricItemViewModel>();
            DefectRateTrend = new ObservableCollection<DashboardDefectRateTrendItemViewModel>();

            TodayCommand = new AsyncRelayCommand(SetTodayAsync);
            ThisWeekCommand = new AsyncRelayCommand(SetThisWeekAsync);
            ThisMonthCommand = new AsyncRelayCommand(SetThisMonthAsync);
            RefreshCommand = new AsyncRelayCommand(LoadAsync);
        }

        public ObservableCollection<DashboardKpiCardItemViewModel> KpiCards { get; }

        public ObservableCollection<DashboardStatusSegmentItemViewModel> OutsourceSegments { get; }

        public ObservableCollection<DashboardStatusSegmentItemViewModel> InspectionSegments { get; }

        public ObservableCollection<DashboardFlowStepItemViewModel> FlowSteps { get; }

        public ObservableCollection<DashboardAlertItemViewModel> Alerts { get; }

        public ObservableCollection<DashboardQualityMetricItemViewModel> QualityMetrics { get; }

        public ObservableCollection<DashboardDefectRateTrendItemViewModel> DefectRateTrend { get; }

        public ICommand TodayCommand { get; }

        public ICommand ThisWeekCommand { get; }

        public ICommand ThisMonthCommand { get; }

        public ICommand RefreshCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public DateTime FromDate
        {
            get => _fromDate;
            set
            {
                if (SetProperty(ref _fromDate, value))
                {
                    OnPropertyChanged(nameof(PeriodText));
                }
            }
        }

        public DateTime ToDate
        {
            get => _toDate;
            set
            {
                if (SetProperty(ref _toDate, value))
                {
                    OnPropertyChanged(nameof(PeriodText));
                }
            }
        }

        public DashboardSummaryDto? Summary
        {
            get => _summary;
            private set
            {
                if (SetProperty(ref _summary, value))
                {
                    RaiseSummaryDisplayProperties();
                }
            }
        }

        public string PeriodText => $"{FromDate:yyyy-MM-dd}  ~  {ToDate:yyyy-MM-dd}";

        public string OutsourceTotalText => $"전체 {Summary?.Outsource.TotalCount ?? 0:N0}건";

        public string OutsourceWorkDoneRateText => $"{Summary?.Outsource.WorkDoneRate ?? 0:N0}%";

        public string OutsourceShippedRateText => $"{Summary?.Outsource.ShippedRate ?? 0:N0}%";

        public double OutsourceWorkDoneRate => Summary?.Outsource.WorkDoneRate ?? 0;

        public double OutsourceShippedRate => Summary?.Outsource.ShippedRate ?? 0;

        public string InspectionTotalText => $"전체 {Summary?.Inspection.TotalCount ?? 0:N0}건";

        public string InspectionDoneRateText => $"{Summary?.Inspection.DoneRate ?? 0:N0}%";

        public double InspectionDoneRate => Summary?.Inspection.DoneRate ?? 0;

        public string QualityInspectedQtyText => FormatInt(Summary?.Quality.InspectedQty);

        public string QualityGoodQtyText => FormatInt(Summary?.Quality.GoodQty);

        public string QualityDefectQtyText => FormatInt(Summary?.Quality.DefectQty);

        public string QualityDefectShipQtyText => FormatInt(Summary?.Quality.DefectShipQty);

        public string QualityGoodRateText => $"{Summary?.Quality.GoodRate ?? 0:N1}%";

        public string QualityDefectRateText => $"{Summary?.Quality.DefectRate ?? 0:N1}%";

        public string QualityDefectShipRateText => $"{Summary?.Quality.DefectShipRate ?? 0:N1}%";

        public async Task InitializeAsync()
        {
            await LoadAsync();
        }

        private async Task SetTodayAsync()
        {
            var today = DateTime.Today;

            FromDate = today;
            ToDate = today;

            await LoadAsync();
        }

        private async Task SetThisWeekAsync()
        {
            var today = DateTime.Today;
            var diff = ((int)today.DayOfWeek + 6) % 7;

            FromDate = today.AddDays(-diff);
            ToDate = today;

            await LoadAsync();
        }

        private async Task SetThisMonthAsync()
        {
            var today = DateTime.Today;

            FromDate = new DateTime(today.Year, today.Month, 1);
            ToDate = today;

            await LoadAsync();
        }

        private async Task LoadAsync()
        {
            if (FromDate.Date > ToDate.Date)
            {
                _messageService.ShowWarning("조회 시작일은 종료일보다 클 수 없습니다.");
                return;
            }

            IsLoading = true;

            try
            {
                var route = BuildSummaryUrl();

                var result = await _apiClient.GetAsync<DashboardSummaryDto>(route);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "대시보드 조회 중 오류가 발생했습니다.");
                    return;
                }

                Summary = result.Data;

                RebuildDashboardItems(result.Data);
            }
            finally
            {
                IsLoading = false;
            }
        }

        private string BuildSummaryUrl()
        {
            return $"{ApiRoutes.DashboardSummary}?from_date={FromDate:yyyy-MM-dd}&to_date={ToDate:yyyy-MM-dd}";
        }

        private void RebuildDashboardItems(DashboardSummaryDto summary)
        {
            RebuildKpiCards(summary);
            RebuildOutsourceSegments(summary);
            RebuildInspectionSegments(summary);
            RebuildFlowSteps(summary);
            RebuildAlerts(summary);
            RebuildQualityMetrics(summary);
            RebuildDefectRateTrend(summary);
        }

        private void RebuildKpiCards(DashboardSummaryDto summary)
        {
            KpiCards.Clear();

            KpiCards.Add(new DashboardKpiCardItemViewModel(
                "총 발주건수",
                $"{summary.Kpi.TotalOrderCount:N0}건",
                "발주 등록 기준",
                "▣",
                "#DBEAFE",
                "#2563EB"));

            KpiCards.Add(new DashboardKpiCardItemViewModel(
                "LOT 생성대기",
                $"{summary.Kpi.LotWaitingCount:N0}건",
                "LOT 미생성 발주",
                "▦",
                "#EDE9FE",
                "#7C3AED"));

            KpiCards.Add(new DashboardKpiCardItemViewModel(
                "외주 진행중",
                $"{summary.Kpi.OutsourceInProgressCount:N0}건",
                "작업완료 전 외주",
                "▣",
                "#CCFBF1",
                "#0F766E"));

            KpiCards.Add(new DashboardKpiCardItemViewModel(
                "검수 대기",
                $"{summary.Kpi.InspectionWaitingCount:N0}건",
                "검수대기 스케줄",
                "⌕",
                "#FEF3C7",
                "#D97706"));

            KpiCards.Add(new DashboardKpiCardItemViewModel(
                "검수 완료율",
                $"{summary.Kpi.InspectionDoneRate:N0}%",
                "전체 검수 대비 완료",
                "✓",
                "#DCFCE7",
                "#16A34A"));

            KpiCards.Add(new DashboardKpiCardItemViewModel(
                "불량률",
                $"{summary.Kpi.DefectRate:N1}%",
                "검수수량 대비 불량",
                "!",
                "#FEE2E2",
                "#DC2626"));
        }

        private void RebuildOutsourceSegments(DashboardSummaryDto summary)
        {
            OutsourceSegments.Clear();

            foreach (var segment in summary.Outsource.Segments)
            {
                OutsourceSegments.Add(
                    DashboardStatusSegmentItemViewModel.FromDto(segment));
            }
        }

        private void RebuildInspectionSegments(DashboardSummaryDto summary)
        {
            InspectionSegments.Clear();

            foreach (var segment in summary.Inspection.Segments)
            {
                InspectionSegments.Add(
                    DashboardStatusSegmentItemViewModel.FromDto(segment));
            }
        }

        private void RebuildFlowSteps(DashboardSummaryDto summary)
        {
            FlowSteps.Clear();

            FlowSteps.Add(new DashboardFlowStepItemViewModel(
                "발주",
                $"{summary.Flow.OrderCount:N0}건",
                "▣",
                "#2563EB",
                false));

            FlowSteps.Add(new DashboardFlowStepItemViewModel(
                "LOT 생성",
                $"{summary.Flow.LotCreatedCount:N0}건",
                "▦",
                "#7C3AED",
                true));

            FlowSteps.Add(new DashboardFlowStepItemViewModel(
                "외주지시",
                $"{summary.Flow.OutsourceInstructionCount:N0}건",
                "▣",
                "#0F766E",
                true));

            FlowSteps.Add(new DashboardFlowStepItemViewModel(
                "외주완료",
                $"{summary.Flow.OutsourceDoneCount:N0}건",
                "▣",
                "#65A30D",
                true));

            FlowSteps.Add(new DashboardFlowStepItemViewModel(
                "검수완료",
                $"{summary.Flow.InspectionDoneCount:N0}건",
                "✓",
                "#2563EB",
                true));
        }

        private void RebuildAlerts(DashboardSummaryDto summary)
        {
            Alerts.Clear();

            foreach (var alert in summary.Alerts)
            {
                Alerts.Add(DashboardAlertItemViewModel.FromDto(alert));
            }
        }

        private void RebuildQualityMetrics(DashboardSummaryDto summary)
        {
            QualityMetrics.Clear();

            QualityMetrics.Add(new DashboardQualityMetricItemViewModel(
                "총 검수수량",
                $"{summary.Quality.InspectedQty:N0}",
                $"양품률 {summary.Quality.GoodRate:N1}%",
                "#2563EB"));

            QualityMetrics.Add(new DashboardQualityMetricItemViewModel(
                "양품수량",
                $"{summary.Quality.GoodQty:N0}",
                "검수 합격 수량",
                "#16A34A"));

            QualityMetrics.Add(new DashboardQualityMetricItemViewModel(
                "불량수량",
                $"{summary.Quality.DefectQty:N0}",
                $"불량률 {summary.Quality.DefectRate:N1}%",
                "#DC2626"));

            QualityMetrics.Add(new DashboardQualityMetricItemViewModel(
                "불량출고수량",
                $"{summary.Quality.DefectShipQty:N0}",
                $"불량출고율 {summary.Quality.DefectShipRate:N1}%",
                "#D97706"));
        }

        private void RebuildDefectRateTrend(DashboardSummaryDto summary)
        {
            DefectRateTrend.Clear();

            var items = summary.DefectRateTrend ?? new List<DashboardDefectRateTrendDto>();
            var maxRate = items.Any()
                ? Math.Max(items.Max(x => x.DefectRate), 1)
                : 1;

            foreach (var item in items)
            {
                DefectRateTrend.Add(
                    DashboardDefectRateTrendItemViewModel.FromDto(
                        item,
                        maxRate));
            }
        }

        private void RaiseSummaryDisplayProperties()
        {
            OnPropertyChanged(nameof(OutsourceTotalText));
            OnPropertyChanged(nameof(OutsourceWorkDoneRateText));
            OnPropertyChanged(nameof(OutsourceShippedRateText));
            OnPropertyChanged(nameof(OutsourceWorkDoneRate));
            OnPropertyChanged(nameof(OutsourceShippedRate));

            OnPropertyChanged(nameof(InspectionTotalText));
            OnPropertyChanged(nameof(InspectionDoneRateText));
            OnPropertyChanged(nameof(InspectionDoneRate));

            OnPropertyChanged(nameof(QualityInspectedQtyText));
            OnPropertyChanged(nameof(QualityGoodQtyText));
            OnPropertyChanged(nameof(QualityDefectQtyText));
            OnPropertyChanged(nameof(QualityDefectShipQtyText));
            OnPropertyChanged(nameof(QualityGoodRateText));
            OnPropertyChanged(nameof(QualityDefectRateText));
            OnPropertyChanged(nameof(QualityDefectShipRateText));
        }

        private static string FormatInt(int? value)
        {
            return value.HasValue ? value.Value.ToString("N0") : "0";
        }
    }

    public class DashboardKpiCardItemViewModel : ViewModelBase
    {
        public DashboardKpiCardItemViewModel(
            string title,
            string value,
            string subText,
            string iconText,
            string iconBackground,
            string iconForeground)
        {
            Title = title;
            Value = value;
            SubText = subText;
            IconText = iconText;
            IconBackground = iconBackground;
            IconForeground = iconForeground;
        }

        public string Title { get; }

        public string Value { get; }

        public string SubText { get; }

        public string IconText { get; }

        public string IconBackground { get; }

        public string IconForeground { get; }
    }

    public class DashboardStatusSegmentItemViewModel : ViewModelBase
    {
        public string Key { get; private set; } = string.Empty;

        public string Label { get; private set; } = string.Empty;

        public int Count { get; private set; }

        public double Percent { get; private set; }

        public string Color { get; private set; } = "#CBD5E1";

        public double BarWidth { get; private set; }

        public string DisplayText => $"{Count:N0} ({Percent:N0}%)";

        public static DashboardStatusSegmentItemViewModel FromDto(
            DashboardStatusSegmentDto dto)
        {
            var percent = dto.Percent;
            var barWidth = percent <= 0
                ? 0
                : Math.Max(28, percent * 4);

            return new DashboardStatusSegmentItemViewModel
            {
                Key = dto.Key,
                Label = dto.Label,
                Count = dto.Count,
                Percent = percent,
                Color = dto.Color,
                BarWidth = barWidth
            };
        }
    }

    public class DashboardFlowStepItemViewModel : ViewModelBase
    {
        public DashboardFlowStepItemViewModel(
            string title,
            string value,
            string iconText,
            string color,
            bool showArrow)
        {
            Title = title;
            Value = value;
            IconText = iconText;
            Color = color;
            ShowArrow = showArrow;
        }

        public string Title { get; }

        public string Value { get; }

        public string IconText { get; }

        public string Color { get; }

        public bool ShowArrow { get; }
    }

    public class DashboardAlertItemViewModel : ViewModelBase
    {
        public string Key { get; private set; } = string.Empty;

        public string Title { get; private set; } = string.Empty;

        public string Description { get; private set; } = string.Empty;

        public int Count { get; private set; }

        public string Color { get; private set; } = "#EF4444";

        public string CountText => $"{Count:N0}건";

        public static DashboardAlertItemViewModel FromDto(DashboardAlertDto dto)
        {
            return new DashboardAlertItemViewModel
            {
                Key = dto.Key,
                Title = dto.Title,
                Description = dto.Description,
                Count = dto.Count,
                Color = dto.Color
            };
        }
    }

    public class DashboardQualityMetricItemViewModel : ViewModelBase
    {
        public DashboardQualityMetricItemViewModel(
            string title,
            string value,
            string subText,
            string color)
        {
            Title = title;
            Value = value;
            SubText = subText;
            Color = color;
        }

        public string Title { get; }

        public string Value { get; }

        public string SubText { get; }

        public string Color { get; }
    }

    public class DashboardDefectRateTrendItemViewModel : ViewModelBase
    {
        public string DateText { get; private set; } = string.Empty;

        public double DefectRate { get; private set; }

        public string DefectRateText => $"{DefectRate:N1}";

        public double BarHeight { get; private set; }

        public static DashboardDefectRateTrendItemViewModel FromDto(
            DashboardDefectRateTrendDto dto,
            double maxRate)
        {
            var barHeight = maxRate <= 0
                ? 0
                : Math.Max(8, (dto.DefectRate / maxRate) * 70);

            return new DashboardDefectRateTrendItemViewModel
            {
                DateText = dto.Date.ToString("M/d"),
                DefectRate = dto.DefectRate,
                BarHeight = barHeight
            };
        }
    }
}