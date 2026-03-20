using System;
using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.OrderLines.Dtos
{
    public class OrderLineCreateHeaderEditModel : ViewModelBase
    {
        private string _orderNo = string.Empty;
        private DateTime _orderDate = DateTime.Today;
        private DateTime _dueDate = DateTime.Today;
        private long? _partnerId;
        private string _partnerName = string.Empty;

        public string OrderNo
        {
            get => _orderNo;
            set => SetProperty(ref _orderNo, value);
        }

        public DateTime OrderDate
        {
            get => _orderDate;
            set => SetProperty(ref _orderDate, value);
        }

        public DateTime DueDate
        {
            get => _dueDate;
            set => SetProperty(ref _dueDate, value);
        }

        public long? PartnerId
        {
            get => _partnerId;
            set => SetProperty(ref _partnerId, value);
        }

        public string PartnerName
        {
            get => _partnerName;
            set => SetProperty(ref _partnerName, value);
        }

        public void Clear()
        {
            OrderNo = string.Empty;
            OrderDate = DateTime.Today;
            DueDate = DateTime.Today;
            PartnerId = null;
            PartnerName = string.Empty;
        }
    }
}