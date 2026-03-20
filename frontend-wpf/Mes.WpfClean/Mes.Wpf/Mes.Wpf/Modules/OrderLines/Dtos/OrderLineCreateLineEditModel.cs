using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.OrderLines.Dtos
{
    public class OrderLineCreateLineEditModel : ViewModelBase
    {
        private int _lineNo;
        private long? _productId;
        private string _productCode = string.Empty;
        private string _productName = string.Empty;
        private string _productSpec = string.Empty;
        private string _uom = string.Empty;
        private int _orderQty;
        private string? _memo;
        private long? _drawingId;
        private string? _drawingNo;

        public int LineNo
        {
            get => _lineNo;
            set => SetProperty(ref _lineNo, value);
        }

        public long? ProductId
        {
            get => _productId;
            set => SetProperty(ref _productId, value);
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

        public string ProductSpec
        {
            get => _productSpec;
            set => SetProperty(ref _productSpec, value);
        }

        public string Uom
        {
            get => _uom;
            set => SetProperty(ref _uom, value);
        }

        public int OrderQty
        {
            get => _orderQty;
            set => SetProperty(ref _orderQty, value);
        }

        public string? Memo
        {
            get => _memo;
            set => SetProperty(ref _memo, value);
        }

        public long? DrawingId
        {
            get => _drawingId;
            set => SetProperty(ref _drawingId, value);
        }

        public string? DrawingNo
        {
            get => _drawingNo;
            set => SetProperty(ref _drawingNo, value);
        }

        public void ApplyProduct(OrderLineProductLookupDto? product)
        {
            if (product == null)
            {
                ProductId = null;
                ProductCode = string.Empty;
                ProductName = string.Empty;
                ProductSpec = string.Empty;
                Uom = string.Empty;
                DrawingId = null;
                DrawingNo = string.Empty;
                return;
            }

            ProductId = product.ProductId;
            ProductCode = product.ProductCode ?? string.Empty;
            ProductName = product.ProductName ?? string.Empty;
            ProductSpec = product.ProductSpec ?? string.Empty;
            Uom = product.Uom ?? string.Empty;
            DrawingId = product.DrawingId;
            DrawingNo = product.DrawingNo ?? string.Empty;
        }

        public void Clear()
        {
            ProductId = null;
            ProductCode = string.Empty;
            ProductName = string.Empty;
            ProductSpec = string.Empty;
            Uom = string.Empty;
            OrderQty = 0;
            Memo = string.Empty;
            DrawingId = null;
            DrawingNo = string.Empty;
        }
    }
}