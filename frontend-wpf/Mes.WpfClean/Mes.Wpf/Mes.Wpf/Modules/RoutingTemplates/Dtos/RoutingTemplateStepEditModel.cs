using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.RoutingTemplates.Dtos
{
    public class RoutingTemplateStepEditModel : ViewModelBase
    {
        private long? _routingStepId;
        private long? _routingTemplateId;
        private string _templateCode = string.Empty;
        private string _templateName = string.Empty;
        private string _stepCode = string.Empty;
        private long? _processId;
        private string _processCode = string.Empty;
        private string _processName = string.Empty;
        private int _sequence = 1;
        private bool _isActive = true;

        public long? RoutingStepId
        {
            get => _routingStepId;
            set => SetProperty(ref _routingStepId, value);
        }

        public long? RoutingTemplateId
        {
            get => _routingTemplateId;
            set => SetProperty(ref _routingTemplateId, value);
        }

        public string TemplateCode
        {
            get => _templateCode;
            set => SetProperty(ref _templateCode, value);
        }

        public string TemplateName
        {
            get => _templateName;
            set => SetProperty(ref _templateName, value);
        }

        public string StepCode
        {
            get => _stepCode;
            set => SetProperty(ref _stepCode, value);
        }

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

        public int Sequence
        {
            get => _sequence;
            set => SetProperty(ref _sequence, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(RoutingTemplateStepDto dto, RoutingTemplateDto templateDto)
        {
            RoutingStepId = dto.RoutingTemplateStepId;
            RoutingTemplateId = dto.RoutingTemplateId;
            TemplateCode = templateDto.TemplateCode;
            TemplateName = templateDto.TemplateName;
            StepCode = dto.RoutingTemplateStepId.ToString();
            ProcessId = dto.ProcessId;
            ProcessCode = dto.ProcessCode;
            ProcessName = dto.ProcessName;
            Sequence = dto.StepSeq;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            RoutingStepId = null;
            RoutingTemplateId = null;
            TemplateCode = string.Empty;
            TemplateName = string.Empty;
            StepCode = string.Empty;
            ProcessId = null;
            ProcessCode = string.Empty;
            ProcessName = string.Empty;
            Sequence = 1;
            IsActive = true;
        }
    }
}