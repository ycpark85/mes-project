using Mes.Wpf.Core.Common;
using Mes.Wpf.Modules.DefectTypes.Dtos;

namespace Mes.Wpf.Core.Models
{
    public class DefectTypeEditModel : BindableBase
    {
        private long? _defectTypeId;
        private string _defectCode = string.Empty;
        private string _defectName = string.Empty;
        private string? _memo;
        private bool _isActive = true;

        public long? DefectTypeId
        {
            get => _defectTypeId;
            set => SetProperty(ref _defectTypeId, value);
        }

        public string DefectCode
        {
            get => _defectCode;
            set => SetProperty(ref _defectCode, value);
        }

        public string DefectName
        {
            get => _defectName;
            set => SetProperty(ref _defectName, value);
        }

        public string? Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(DefectTypeDto dto)
        {
            DefectTypeId = dto.DefectTypeId;
            DefectCode = dto.DefectCode;
            DefectName = dto.DefectName;
            Memo = dto.Memo;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            DefectTypeId = null;
            DefectCode = string.Empty;
            DefectName = string.Empty;
            Memo = string.Empty;
            IsActive = true;
        }
    }
}