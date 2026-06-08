namespace Mes.Wpf.Core.Models
{
    public class ApiResult<T>
    {
        public bool Success { get; set; }

        public string? Message { get; set; }

        public T? Data { get; set; }
    }

    public class ApiFileDownload
    {
        public byte[] Content { get; set; } = System.Array.Empty<byte>();

        public string FileName { get; set; } = string.Empty;

        public string? ContentType { get; set; }
    }
}
