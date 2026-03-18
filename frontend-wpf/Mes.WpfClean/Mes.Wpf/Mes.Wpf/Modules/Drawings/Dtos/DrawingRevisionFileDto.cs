using System.Text.Json.Serialization;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingRevisionFileDto
    {
        [JsonPropertyName("revision_file_id")]
        public long RevisionFileId { get; set; }

        [JsonPropertyName("revision_id")]
        public long RevisionId { get; set; }

        [JsonPropertyName("file_kind")]
        public string FileKind { get; set; } = string.Empty;

        [JsonPropertyName("file_uri")]
        public string FileUri { get; set; } = string.Empty;

        [JsonPropertyName("original_filename")]
        public string OriginalFilename { get; set; } = string.Empty;

        [JsonPropertyName("content_type")]
        public string? ContentType { get; set; }

        [JsonPropertyName("file_size")]
        public long? FileSize { get; set; }
    }
}