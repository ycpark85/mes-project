using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.BohyunOutsourceManagement.Dtos
{
    public class BohyunOutsourceWorkDoneRequest
    {
        [JsonPropertyName("work_done_sheet_qty")]
        public int WorkDoneSheetQty { get; set; }

        [JsonPropertyName("outsource_processing_fee")]
        public decimal? OutsourceProcessingFee { get; set; }

        [JsonPropertyName("remark")]
        public string? Remark { get; set; }
    }
}