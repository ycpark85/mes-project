using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.DefectTypes.Dtos
{
    public class DefectTypeEditModel : ViewModelBase
    {
        private long? _defectTypeId;
        private string _defectCode = string.Empty;
        private string _category1Name = string.Empty;
        private string _category2Name = string.Empty;
        private string _memo = string.Empty;
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

        public string Memo
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
            Category1Name = dto.Category1Name;
            Category2Name = dto.Category2Name;
            Memo = dto.Memo ?? string.Empty;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            DefectTypeId = null;
            DefectCode = string.Empty;
            Category1Name = string.Empty;
            Category2Name = string.Empty;
            Memo = string.Empty;
            IsActive = true;
        }
    }
}