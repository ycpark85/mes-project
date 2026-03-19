using System.Threading.Tasks;

namespace Mes.Wpf.Core.Interfaces
{
    public interface IDrawingFileOpener
    {
        Task OpenRevisionFileAsync(string downloadUrl, string? fileName);
    }
}