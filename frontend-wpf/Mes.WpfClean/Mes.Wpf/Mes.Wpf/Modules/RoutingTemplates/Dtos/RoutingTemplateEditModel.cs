using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.RoutingTemplates.Dtos
{
    public class RoutingTemplateEditModel : ViewModelBase
    {
        private long? _routingTemplateId;
        private string _templateCode = string.Empty;
        private string _templateName = string.Empty;
        private bool _isActive = true;

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

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(RoutingTemplateDto dto)
        {
            RoutingTemplateId = dto.RoutingTemplateId;
            TemplateCode = dto.TemplateCode;
            TemplateName = dto.TemplateName;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            RoutingTemplateId = null;
            TemplateCode = string.Empty;
            TemplateName = string.Empty;
            IsActive = true;
        }
    }
}