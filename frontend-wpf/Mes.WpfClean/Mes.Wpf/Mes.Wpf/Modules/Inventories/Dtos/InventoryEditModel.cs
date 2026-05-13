using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Inventories.Dtos
{
    public class InventoryEditModel : ViewModelBase
    {
        private long? _productId;
        private string _productCode = string.Empty;
        private string _productName = string.Empty;
        private string _uom = string.Empty;
        private int _currentQty;

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

        public string Uom
        {
            get => _uom;
            set => SetProperty(ref _uom, value);
        }

        public int CurrentQty
        {
            get => _currentQty;
            set => SetProperty(ref _currentQty, value);
        }

        public void LoadFromDto(InventoryDto dto)
        {
            ProductId = dto.ProductId;
            ProductCode = dto.ProductCode;
            ProductName = dto.ProductName;
            Uom = dto.Uom;
            CurrentQty = dto.CurrentQty;
        }

        public void Clear()
        {
            ProductId = null;
            ProductCode = string.Empty;
            ProductName = string.Empty;
            Uom = string.Empty;
            CurrentQty = 0;
        }
    }
}