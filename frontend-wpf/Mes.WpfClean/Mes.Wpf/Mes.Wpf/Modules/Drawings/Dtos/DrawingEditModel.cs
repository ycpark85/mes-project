using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingEditModel : ViewModelBase
    {
        private long? _drawingId;
        private string _drawingNo = string.Empty;
        private long? _currentRevisionId;
        private bool _isActive = true;

        public long? DrawingId
        {
            get => _drawingId;
            set => SetProperty(ref _drawingId, value);
        }

        public string DrawingNo
        {
            get => _drawingNo;
            set => SetProperty(ref _drawingNo, value);
        }

        public long? CurrentRevisionId
        {
            get => _currentRevisionId;
            set => SetProperty(ref _currentRevisionId, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(DrawingDto dto)
        {
            DrawingId = dto.DrawingId;
            DrawingNo = dto.DrawingNo;
            CurrentRevisionId = dto.CurrentRevisionId;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            DrawingId = null;
            DrawingNo = string.Empty;
            CurrentRevisionId = null;
            IsActive = true;
        }
    }
}