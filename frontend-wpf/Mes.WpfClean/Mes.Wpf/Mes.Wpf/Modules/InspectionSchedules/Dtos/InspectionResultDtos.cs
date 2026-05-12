using System;
using System.Collections.ObjectModel;
using System.Text.Json.Serialization;
using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.InspectionSchedules.Dtos
{
    public class InspectionResultResponse
    {
        [JsonPropertyName("result")]
        public InspectionResultDto? Result { get; set; }

        [JsonPropertyName("accumulated")]
        public InspectionAccumulatedSummaryDto? Accumulated { get; set; }
    }

    public class InspectionAccumulatedSummaryDto
    {
        [JsonPropertyName("good_qty")]
        public int GoodQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("defect_ship_qty")]
        public int DefectShipQty { get; set; }

        [JsonPropertyName("inspected_qty")]
        public int InspectedQty { get; set; }
    }

    public class InspectionResultDto
    {
        [JsonPropertyName("inspection_result_id")]
        public int InspectionResultId { get; set; }

        [JsonPropertyName("inspection_schedule_id")]
        public int InspectionScheduleId { get; set; }

        [JsonPropertyName("good_qty")]
        public int GoodQty { get; set; }

        [JsonPropertyName("defect_ship_qty")]
        public int DefectShipQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("is_partial")]
        public bool IsPartial { get; set; }

        [JsonPropertyName("next_inspection_date")]
        public DateTime? NextInspectionDate { get; set; }

        [JsonPropertyName("partial_reason")]
        public string? PartialReason { get; set; }

        [JsonPropertyName("defects")]
        public ObservableCollection<InspectionResultDefectDto> Defects { get; set; } = new();
    }

    public class InspectionResultDefectDto
    {
        [JsonPropertyName("inspection_defect_line_id")]
        public int InspectionDefectLineId { get; set; }

        [JsonPropertyName("defect_type_id")]
        public int DefectTypeId { get; set; }

        [JsonPropertyName("disposition")]
        public string? Disposition { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("attachments")]
        public ObservableCollection<DefectAttachmentOutDto> Attachments { get; set; } = new();
    }

    public class DefectAttachmentOutDto
    {
        [JsonPropertyName("inspection_defect_attachment_id")]
        public int InspectionDefectAttachmentId { get; set; }

        [JsonPropertyName("file_uri")]
        public string FileUri { get; set; } = string.Empty;

        [JsonPropertyName("file_name")]
        public string? FileName { get; set; }

        [JsonPropertyName("mime_type")]
        public string? MimeType { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }

    public class DefectAttachmentUploadResponse
    {
        [JsonPropertyName("file_uri")]
        public string FileUri { get; set; } = string.Empty;

        [JsonPropertyName("file_name")]
        public string FileName { get; set; } = string.Empty;

        [JsonPropertyName("mime_type")]
        public string? MimeType { get; set; }

        [JsonPropertyName("file_size")]
        public int FileSize { get; set; }
    }

    public class InspectionResultUpsertRequest
    {
        [JsonPropertyName("good_qty")]
        public int GoodQty { get; set; }

        [JsonPropertyName("defect_ship_qty")]
        public int DefectShipQty { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("is_partial")]
        public bool IsPartial { get; set; }

        [JsonPropertyName("next_inspection_date")]
        public DateTime? NextInspectionDate { get; set; }

        [JsonPropertyName("partial_reason")]
        public string? PartialReason { get; set; }

        [JsonPropertyName("defects")]
        public ObservableCollection<InspectionResultDefectRequest> Defects { get; set; } = new();
    }

    public class InspectionResultDefectRequest
    {
        [JsonPropertyName("defect_type_id")]
        public int DefectTypeId { get; set; }

        [JsonPropertyName("defect_qty")]
        public int DefectQty { get; set; }

        [JsonPropertyName("disposition")]
        public string Disposition { get; set; } = "NOT_SHIPPABLE";

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }

        [JsonPropertyName("attachments")]
        public ObservableCollection<DefectAttachmentRequest> Attachments { get; set; } = new();
    }

    public class DefectAttachmentRequest
    {
        [JsonPropertyName("file_uri")]
        public string FileUri { get; set; } = string.Empty;

        [JsonPropertyName("file_name")]
        public string? FileName { get; set; }

        [JsonPropertyName("mime_type")]
        public string? MimeType { get; set; }

        [JsonPropertyName("memo")]
        public string? Memo { get; set; }
    }

    public class InspectionResultUpsertResponse
    {
        [JsonPropertyName("schedule_status")]
        public string? ScheduleStatus { get; set; }

        [JsonPropertyName("created_next_schedule_id")]
        public int? CreatedNextScheduleId { get; set; }
    }

    public class InspectionResultDefectEditModel : ViewModelBase
    {
        private int? _defectTypeId;
        private string _defectCode = string.Empty;
        private string _category1Name = string.Empty;
        private string _category2Name = string.Empty;
        private string _defectTypeMemo = string.Empty;
        private ObservableCollection<DefectAttachmentEditModel> _attachments = new();

        public int? DefectTypeId
        {
            get => _defectTypeId;
            set => SetProperty(ref _defectTypeId, value);
        }

        public string DefectCode
        {
            get => _defectCode;
            set => SetProperty(ref _defectCode, value);
        }

        public string Category1Name
        {
            get => _category1Name;
            set => SetProperty(ref _category1Name, value);
        }

        public string Category2Name
        {
            get => _category2Name;
            set => SetProperty(ref _category2Name, value);
        }

        public string DefectTypeMemo
        {
            get => _defectTypeMemo;
            set => SetProperty(ref _defectTypeMemo, value);
        }

        // 기존 SaveAsync에서 defect.Memo를 사용하고 있으므로 영향 최소화를 위해 유지
        public string Memo
        {
            get => DefectTypeMemo;
            set => DefectTypeMemo = value;
        }

        public ObservableCollection<DefectAttachmentEditModel> Attachments
        {
            get => _attachments;
            set => SetProperty(ref _attachments, value);
        }

        public void Clear()
        {
            DefectTypeId = null;
            DefectCode = string.Empty;
            Category1Name = string.Empty;
            Category2Name = string.Empty;
            DefectTypeMemo = string.Empty;
            Attachments.Clear();
        }
    }

    public class DefectAttachmentEditModel : ViewModelBase
    {
        private string _fileUri = string.Empty;
        private string _fileName = string.Empty;
        private string _mimeType = string.Empty;
        private string _memo = string.Empty;

        public string FileUri
        {
            get => _fileUri;
            set => SetProperty(ref _fileUri, value);
        }

        public string FileName
        {
            get => _fileName;
            set => SetProperty(ref _fileName, value);
        }

        public string MimeType
        {
            get => _mimeType;
            set => SetProperty(ref _mimeType, value);
        }

        public string Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }
    }
}