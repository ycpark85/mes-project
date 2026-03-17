using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Partners.Dtos
{
    public class PartnerBulkUploadRowModel : ViewModelBase
    {
        private int _rowNumber;
        private string _partnerType = "CUSTOMER";
        private string _name = string.Empty;
        private string _businessNo = string.Empty;
        private bool _isActive = true;
        private bool _isValid = true;
        private string _errorMessage = string.Empty;

        public int RowNumber
        {
            get => _rowNumber;
            set => SetProperty(ref _rowNumber, value);
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

        public string BusinessNo
        {
            get => _businessNo;
            set => SetProperty(ref _businessNo, value);
        }

        public bool IsActive
        {
            get => _isActive;
            set => SetProperty(ref _isActive, value);
        }

        public bool IsValid
        {
            get => _isValid;
            set => SetProperty(ref _isValid, value);
        }

        public string ErrorMessage
        {
            get => _errorMessage;
            set => SetProperty(ref _errorMessage, value);
        }

        public void ClearValidation()
        {
            IsValid = true;
            ErrorMessage = string.Empty;
        }
    }
}