using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Processes.Dtos
{
    public class ProcessEditModel : ViewModelBase
    {
        private long? _processId;
        private string _processCode = string.Empty;
        private string _processName = string.Empty;
        private string _processType = "INTERNAL";
        private bool _isActive = true;

        public long? ProcessId
        {
            get => _processId;
            set => SetProperty(ref _processId, value);
        }

        public string ProcessCode
        {
            get => _processCode;
            set => SetProperty(ref _processCode, value);
        }

        public string ProcessName
        {
            get => _processName;
            set => SetProperty(ref _processName, value);
        }

        public string ProcessType
        {
            get => _processType;
            set => SetProperty(ref _processType, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(ProcessDto dto)
        {
            ProcessId = dto.ProcessId;
            ProcessCode = dto.ProcessCode;
            ProcessName = dto.ProcessName;
            ProcessType = dto.ProcessType;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            ProcessId = null;
            ProcessCode = string.Empty;
            ProcessName = string.Empty;
            ProcessType = "INTERNAL";
            IsActive = true;
        }
    }
}