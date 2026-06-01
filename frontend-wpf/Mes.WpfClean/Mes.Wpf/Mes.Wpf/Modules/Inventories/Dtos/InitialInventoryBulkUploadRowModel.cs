using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Inventories.Dtos
{
    public class InitialInventoryBulkUploadRowModel : ViewModelBase
    {
        private int _rowNumber;
        private string _productCode = string.Empty;
        private string _lotNo = string.Empty;
        private int _initialQty;
        private string? _memo;
        private string _status = "대기";
        private string _errorMessage = string.Empty;

        public int RowNumber
        {
            get => _rowNumber;
            set => SetProperty(ref _rowNumber, value);
        }

        public string ProductCode
        {
            get => _productCode;
            set => SetProperty(ref _productCode, value);
        }

        public string LotNo
        {
            get => _lotNo;
            set => SetProperty(ref _lotNo, value);
        }

        public int InitialQty
        {
            get => _initialQty;
            set => SetProperty(ref _initialQty, value);
        }

        public string? Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public string Status
        {
            get => _status;
            set
            {
                if (SetProperty(ref _status, value))
                {
                    OnPropertyChanged(nameof(IsValid));
                }
            }
        }

        public string ErrorMessage
        {
            get => _errorMessage;
            set => SetProperty(ref _errorMessage, value);
        }

        public bool IsValid => Status == "정상";

        public void ClearValidation()
        {
            Status = "정상";
            ErrorMessage = string.Empty;
        }

        public void MarkError(string message)
        {
            Status = "오류";
            ErrorMessage = message;
        }

        public void MarkSkipped(string message)
        {
            Status = "제외";
            ErrorMessage = message;
        }

        public void MarkUploaded()
        {
            Status = "등록완료";
            ErrorMessage = string.Empty;
        }
    }
}
