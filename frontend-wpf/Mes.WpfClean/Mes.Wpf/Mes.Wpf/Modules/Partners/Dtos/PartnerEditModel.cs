using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Partners.Dtos
{
    public class PartnerEditModel : ViewModelBase
    {
        private long? _partnerId;
        private string _partnerType = "CUSTOMER";
        private string _name = string.Empty;
        private string? _businessNo;
        private bool _isActive = true;

        public long? PartnerId
        {
            get => _partnerId;
            set => SetProperty(ref _partnerId, value);
        }

        public string PartnerType
        {
            get => _partnerType;
            set => SetProperty(ref _partnerType, value);
        }

        public string Name
        {
            get => _name;
            set => SetProperty(ref _name, value);
        }

        public string? BusinessNo
        {
            get => _businessNo;
            set => SetProperty(ref _businessNo, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public void LoadFromDto(PartnerDto dto)
        {
            PartnerId = dto.PartnerId;
            PartnerType = dto.PartnerType;
            Name = dto.Name;
            BusinessNo = dto.BusinessNo;
            IsActive = dto.IsActive;
        }

        public void Clear()
        {
            PartnerId = null;
            PartnerType = "CUSTOMER";
            Name = string.Empty;
            BusinessNo = null;
            IsActive = true;
        }
    }
}