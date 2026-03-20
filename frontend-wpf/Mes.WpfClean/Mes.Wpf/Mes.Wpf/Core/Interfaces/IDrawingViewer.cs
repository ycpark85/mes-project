using System.Threading.Tasks;

namespace Mes.Wpf.Core.Interfaces
{
    public interface IDrawingViewer
    {
        Task OpenCurrentDrawingAsync(long drawingId);
    }
}