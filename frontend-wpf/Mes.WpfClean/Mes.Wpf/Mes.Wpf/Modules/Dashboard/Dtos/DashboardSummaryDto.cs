using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Dashboard.Dtos
{
    public class DashboardSummaryDto
    {
        [JsonPropertyName("period")]
        public DashboardPeriodDto Period { get; set; } = new();

        [JsonPropertyName("kpi")]
        public DashboardKpiDto Kpi { get; set; } = new();

        [JsonPropertyName("outsource")]
        public DashboardOutsourceSummaryDto Outsource { get; set; } = new();

        [JsonPropertyName("inspection")]
        public DashboardInspectionSummaryDto Inspection { get; set; } = new();

        [JsonPropertyName("flow")]
        public DashboardFlowDto Flow { get; set; } = new();

        [JsonPropertyName("alerts")]
        public List<DashboardAlertDto> Alerts { get; set; } = new();

        [JsonPropertyName("quality")]
        public DashboardQualitySummaryDto Quality { get; set; } = new();

        [JsonPropertyName("defect_rate_trend")]
        public List<DashboardDefectRateTrendDto> DefectRateTrend { get; set; } = new();
    }

    public class DashboardPeriodDto
    {
        [JsonPropertyName("from_date")]
        public DateTime FromDate { get; set; }

        [JsonPropertyName("to_date")]
        public DateTime ToDate { get; set; }
    }

    public class DashboardKpiDto
    {
        [JsonPropertyName("total_order_count")]
        public int TotalOrderCount { get; set; }

        [JsonPropertyName("lot_waiting_count")]
        public int LotWaitingCount { get; set; }

        [JsonPropertyName("outsource_in_progress_count")]
        public int OutsourceInProgressCount { get; set; }

        [JsonPropertyName("inspection_waiting_count")]
        public int InspectionWaitingCount { get; set; }

        [JsonPropertyName("inspection_done_rate")]
        public double InspectionDoneRate { get; set; }

        [JsonPropertyName("defect_rate")]
        public double DefectRate { get; set; }
    }

    public class DashboardStatusSegmentDto
    {
        [JsonPropertyName("key")]
        public string Key { get; set; } = string.Empty;

        [JsonPropertyName("label")]
        public string Label { get; set; } = string.Empty;

        [JsonPropertyName("count")]
        public int Count { get; set; }

        [JsonPropertyName("percent")]
        public double Percent { get; set; }

        [JsonPropertyName("color")]
        public string Color { get; set; } = "#CBD5E1";
    }

    public class DashboardOutsourceSummaryDto
    {
        [JsonPropertyName("total_count")]
        public int TotalCount { get; set; }

        [JsonPropertyName("instruction_created_count")]
        public int InstructionCreatedCount { get; set; }

        [JsonPropertyName("vendor_received_count")]
        public int VendorReceivedCount { get; set; }

        [JsonPropertyName("work_done_count")]
        public int WorkDoneCount { get; set; }

        [JsonPropertyName("shipped_count")]
        public int ShippedCount { get; set; }

        [JsonPropertyName("work_done_rate")]
        public double WorkDoneRate { get; set; }

        [JsonPropertyName("shipped_rate")]
        public double ShippedRate { get; set; }

        [JsonPropertyName("segments")]
        public List<DashboardStatusSegmentDto> Segments { get; set; } = new();
    }

    public class DashboardInspectionSummaryDto
    {
        [JsonPropertyName("total_count")]
        public int TotalCount { get; set; }

        [JsonPropertyName("waiting_count")]
        public int WaitingCount { get; set; }

        [JsonPropertyName("received_count")]
        public int ReceivedCount { get; set; }

        [JsonPropertyName("in_progress_count")]
        public int InProgressCount { get; set; }

        [JsonPropertyName("partial_done_count")]
        public int PartialDoneCount { get; set; }

        [JsonPropertyName("done_count")]
        public int DoneCount { get; set; }

        [JsonPropertyName("done_rate")]
        public double DoneRate { get; set; }

        [JsonPropertyName("segments")]
        public List<DashboardStatusSegmentDto> Segments { get; set; } = new();
    }

    public class DashboardFlowDto
    {
        [JsonPropertyName("order_count")]
        public int OrderCount { get; set; }

        [JsonPropertyName("lot_created_count")]
        public int LotCreatedCount { get; set; }

        [JsonPropertyName("outsource_instruction_count")]
        public int OutsourceInstructionCount { get; set; }

        [JsonPropertyName("outsource_done_count")]
        public int OutsourceDoneCount { get; set; }

        [JsonPropertyName("inspection_done_count")]
        public int InspectionDoneCount { get; set; }
    }

    public class DashboardAlertDto
    {
        [JsonPropertyName("key")]
        public string Key { get; set; } = string.Empty;

        [JsonPropertyName("title")]
        public string Title { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string Description { get; set; } = string.Empty;

        [JsonPropertyName("count")]
        public int Count { get; set; }

        [JsonPropertyName("color")]
        public string Color { get; set; } = "#EF4444";
    }

    public class DashboardQualitySummaryDto
    {
        [JsonPropertyName("inspected_qty")]
        public int InspectedQty { get; set; }

        [JsonPropertyName("good_qty")]
        public int GoodQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("defect_ship_qty")]
        public int DefectShipQty { get; set; }

        [JsonPropertyName("good_rate")]
        public double GoodRate { get; set; }

        [JsonPropertyName("defect_rate")]
        public double DefectRate { get; set; }

        [JsonPropertyName("defect_ship_rate")]
        public double DefectShipRate { get; set; }
    }

    public class DashboardDefectRateTrendDto
    {
        [JsonPropertyName("date")]
        public DateTime Date { get; set; }

        [JsonPropertyName("inspected_qty")]
        public int InspectedQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("defect_rate")]
        public double DefectRate { get; set; }
    }
}