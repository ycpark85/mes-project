using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Products.Dtos
{
    public class ProductBulkUploadRowModel : ViewModelBase
    {
        private int _rowNumber;
        private string _productCode = string.Empty;
        private string _productName = string.Empty;
        private string _uom = string.Empty;
        private string _drawingNo = string.Empty;
        private string _templateCode = string.Empty;
        private int? _panelWidthMm;
        private int? _panelLengthMm;
        private string? _productSpec;
        private int? _cutQtyPerPanel;
        private bool _isActive = true;
        private bool _isValid = true;
        private string _errorMessage = string.Empty;
        private string? _memo;

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

        public string ProductName
        {
            get => _productName;
            set => SetProperty(ref _productName, value);
        }

        public string Uom
        {
            get => _uom;
            set => SetProperty(ref _uom, value);
        }

        public string DrawingNo
        {
            get => _drawingNo;
            set => SetProperty(ref _drawingNo, value);
        }

        public string TemplateCode
        {
            get => _templateCode;
            set => SetProperty(ref _templateCode, value);
        }

        public int? PanelWidthMm
        {
            get => _panelWidthMm;
            set => SetProperty(ref _panelWidthMm, value);
        }

        public int? PanelLengthMm
        {
            get => _panelLengthMm;
            set => SetProperty(ref _panelLengthMm, value);
        }

        public string? ProductSpec
        {
            get => _productSpec;
            set => SetProperty(ref _productSpec, value);
        }

        public int? CutQtyPerPanel
        {
            get => _cutQtyPerPanel;
            set => SetProperty(ref _cutQtyPerPanel, value);
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

        public string? Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public void ClearValidation()
        {
            IsValid = true;
            ErrorMessage = string.Empty;
        }
    }
}