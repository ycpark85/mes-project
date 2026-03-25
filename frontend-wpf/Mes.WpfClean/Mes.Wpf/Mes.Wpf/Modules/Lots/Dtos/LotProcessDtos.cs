using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;
using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Lots.Dtos
{
    public class LotProcessSearchModel : ViewModelBase
    {
        private DateTime? _createdDateFrom;
        private DateTime? _createdDateTo;
        private DateTime? _dueDateFrom;
        private DateTime? _dueDateTo;
        private string _keyword = string.Empty;

        public DateTime? CreatedDateFrom
        {
            get => _createdDateFrom;
            set => SetProperty(ref _createdDateFrom, value);
        }

        public DateTime? CreatedDateTo
        {
            get => _createdDateTo;
            set => SetProperty(ref _createdDateTo, value);
        }

        public DateTime? DueDateFrom
        {
            get => _dueDateFrom;
            set => SetProperty(ref _dueDateFrom, value);
        }

        public DateTime? DueDateTo
        {
            get => _dueDateTo;
            set => SetProperty(ref _dueDateTo, value);
        }

        public string Keyword
        {
            get => _keyword;
            set => SetProperty(ref _keyword, value);
        }

        public void Clear()
        {
            CreatedDateFrom = null;
            CreatedDateTo = null;
            DueDateFrom = null;
            DueDateTo = null;
            Keyword = string.Empty;
        }
    }

    public class LotListResponseDto
    {
        [JsonPropertyName("items")]
        public List<LotListItemDto> Items { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }

        [JsonPropertyName("page")]
        public int Page { get; set; }

        [JsonPropertyName("size")]
        public int Size { get; set; }
    }

    public class LotListItemDto
    {
        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("order_no")]
        public string OrderNo { get; set; } = string.Empty;

        [JsonPropertyName("partner_name")]
        public string PartnerName { get; set; } = string.Empty;

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("lot_qty")]
        public decimal LotQty { get; set; }

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = string.Empty;

        [JsonPropertyName("due_date")]
        public DateTime? DueDate { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime? CreatedAt { get; set; }
    }

    public class LotDetailDto
    {
        [JsonPropertyName("lot_id")]
        public long LotId { get; set; }

        [JsonPropertyName("lot_no")]
        public string LotNo { get; set; } = string.Empty;

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("order_line_id")]
        public long OrderLineId { get; set; }

        [JsonPropertyName("order_no")]
        public string OrderNo { get; set; } = string.Empty;

        [JsonPropertyName("partner_name")]
        public string PartnerName { get; set; } = string.Empty;

        [JsonPropertyName("product_code")]
        public string ProductCode { get; set; } = string.Empty;

        [JsonPropertyName("product_name")]
        public string ProductName { get; set; } = string.Empty;

        [JsonPropertyName("lot_qty")]
        public decimal LotQty { get; set; }

        [JsonPropertyName("uom")]
        public string Uom { get; set; } = string.Empty;

        [JsonPropertyName("created_date")]
        public DateTime? CreatedDate { get; set; }

        [JsonPropertyName("due_date")]
        public DateTime? DueDate { get; set; }

        [JsonPropertyName("steps")]
        public List<LotStepDto> Steps { get; set; } = new();
    }

    public class LotStepDto
    {
        [JsonPropertyName("lot_step_id")]
        public long LotStepId { get; set; }

        [JsonPropertyName("step_seq")]
        public int StepSeq { get; set; }

        [JsonPropertyName("process_id")]
        public long ProcessId { get; set; }

        [JsonPropertyName("process_code")]
        public string ProcessCode { get; set; } = string.Empty;

        [JsonPropertyName("process_name")]
        public string ProcessName { get; set; } = string.Empty;

        [JsonPropertyName("process_type")]
        public string ProcessType { get; set; } = string.Empty;

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("started_at")]
        public DateTime? StartedAt { get; set; }

        [JsonPropertyName("ended_at")]
        public DateTime? EndedAt { get; set; }

        public bool CanStart =>
            string.Equals(ProcessType, "OUTSOURCE", StringComparison.OrdinalIgnoreCase) &&
            string.Equals(Status, "WAITING", StringComparison.OrdinalIgnoreCase);

        public bool CanComplete =>
            string.Equals(ProcessType, "OUTSOURCE", StringComparison.OrdinalIgnoreCase) &&
            string.Equals(Status, "IN_PROGRESS", StringComparison.OrdinalIgnoreCase);

        public bool IsOutsource =>
            string.Equals(ProcessType, "OUTSOURCE", StringComparison.OrdinalIgnoreCase);
    }
}