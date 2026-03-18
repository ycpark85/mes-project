using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingRevisionDto
    {
        [JsonPropertyName("revision_id")]
        public long RevisionId { get; set; }

        [JsonPropertyName("drawing_id")]
        public long DrawingId { get; set; }

        [JsonPropertyName("rev_no")]
        public string RevNo { get; set; } = string.Empty;

        [JsonPropertyName("file_uri")]
        public string FileUri { get; set; } = string.Empty;

        [JsonPropertyName("files")]
        public List<DrawingRevisionFileDto> Files { get; set; } = new();
    }
}