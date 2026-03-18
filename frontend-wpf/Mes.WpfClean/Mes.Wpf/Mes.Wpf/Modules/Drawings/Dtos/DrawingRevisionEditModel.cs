using System.Linq;
using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Drawings.Dtos
{
    public class DrawingRevisionEditModel : ViewModelBase
    {
        private long? _revisionId;
        private string _revNo = string.Empty;
        private bool _setAsCurrent = true;

        private long? _drawingFileId;
        private string _drawingFileName = string.Empty;

        private long? _originalFileId;
        private string _originalFileName = string.Empty;

        private long? _plateFileId;
        private string _plateFileName = string.Empty;

        public long? RevisionId
        {
            get => _revisionId;
            set => SetProperty(ref _revisionId, value);
        }

        public string RevNo
        {
            get => _revNo;
            set => SetProperty(ref _revNo, value);
        }

        public bool SetAsCurrent
        {
            get => _setAsCurrent;
            set => SetProperty(ref _setAsCurrent, value);
        }

        public long? DrawingFileId
        {
            get => _drawingFileId;
            set => SetProperty(ref _drawingFileId, value);
        }

        public string DrawingFileName
        {
            get => _drawingFileName;
            set => SetProperty(ref _drawingFileName, value);
        }

        public long? OriginalFileId
        {
            get => _originalFileId;
            set => SetProperty(ref _originalFileId, value);
        }

        public string OriginalFileName
        {
            get => _originalFileName;
            set => SetProperty(ref _originalFileName, value);
        }

        public long? PlateFileId
        {
            get => _plateFileId;
            set => SetProperty(ref _plateFileId, value);
        }

        public string PlateFileName
        {
            get => _plateFileName;
            set => SetProperty(ref _plateFileName, value);
        }

        public void LoadFromDto(DrawingRevisionDto dto)
        {
            RevisionId = dto.RevisionId;
            RevNo = dto.RevNo;
            SetAsCurrent = false;

            var drawing = dto.Files.FirstOrDefault(x => x.FileKind == "DRAWING");
            var original = dto.Files.FirstOrDefault(x => x.FileKind == "ORIGINAL");
            var plate = dto.Files.FirstOrDefault(x => x.FileKind == "PLATE");

            DrawingFileId = drawing?.RevisionFileId;
            DrawingFileName = drawing?.OriginalFilename ?? string.Empty;

            OriginalFileId = original?.RevisionFileId;
            OriginalFileName = original?.OriginalFilename ?? string.Empty;

            PlateFileId = plate?.RevisionFileId;
            PlateFileName = plate?.OriginalFilename ?? string.Empty;
        }

        public void Clear()
        {
            RevisionId = null;
            RevNo = string.Empty;
            SetAsCurrent = true;

            DrawingFileId = null;
            DrawingFileName = string.Empty;

            OriginalFileId = null;
            OriginalFileName = string.Empty;

            PlateFileId = null;
            PlateFileName = string.Empty;
        }
    }
}