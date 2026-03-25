using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Modules.Lots.Dtos
{
    public class LotPrimaryCandidateDto : ViewModelBase
    {
        private bool _isSelected;

        public long LotId { get; set; }
        public string LotNo { get; set; } = string.Empty;
        public long OrderLineId { get; set; }
        public int LotQty { get; set; }
        public string Status { get; set; } = string.Empty;
        public string Uom { get; set; } = string.Empty;
        public string? Memo { get; set; }

        public bool IsReworkAllowed =>
            Status == "DONE" || Status == "CANCELED";

        public bool IsSelected
        {
            get => _isSelected;
            set => SetProperty(ref _isSelected, value);
        }
    }
}