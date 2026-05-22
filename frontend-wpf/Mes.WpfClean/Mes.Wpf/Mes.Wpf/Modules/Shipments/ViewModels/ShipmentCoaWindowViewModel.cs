using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Shipments.Dtos;
using System;
using System.ComponentModel;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Input;

namespace Mes.Wpf.Modules.Shipments.ViewModels
{
    public class ShipmentCoaWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private ShipmentCoaDto? _coa;
        private long _orderLineId;

        private string _dimensionWidthCriteria = "-";
        private string _dimensionHeightCriteria = "-";
        private string _dimensionWidthResult = "-";
        private string _dimensionHeightResult = "-";
        private bool _isPrintedProduct;

        public ShipmentCoaWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Edit = new ShipmentCoaEditModel();
            Edit.PropertyChanged += OnEditPropertyChanged;

            SaveCommand = new AsyncRelayCommand(SaveAsync);
            CloseCommand = new RelayCommand(_ => RequestClose?.Invoke());
            PrintCommand = new RelayCommand(_ => RequestPrint?.Invoke());
        }

        public event Action? RequestClose;
        public event Action? RequestPrint;

        public ShipmentCoaEditModel Edit { get; }

        public ICommand SaveCommand { get; }
        public ICommand CloseCommand { get; }
        public ICommand PrintCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public ShipmentCoaDto? Coa
        {
            get => _coa;
            set
            {
                if (SetProperty(ref _coa, value))
                {
                    ApplyCoaToDisplay();
                }
            }
        }

        public string ProductName => Coa?.ProductNameSnapshot ?? "-";
        public string ProductSpec => Coa?.ProductSpecSnapshot ?? "-";
        public string Material => Coa?.MaterialSnapshot ?? "-";
        public string PartnerName => Coa?.PartnerNameSnapshot ?? "-";
        public string LotNos => Coa?.LotNosSnapshot ?? "-";

        public bool IsPrintedProduct
        {
            get => _isPrintedProduct;
            set
            {
                if (SetProperty(ref _isPrintedProduct, value))
                {
                    OnPropertyChanged(nameof(PrintStateResult));
                    OnPropertyChanged(nameof(PrintStateJudgment));
                    OnPropertyChanged(nameof(PrintTypeText));
                }
            }
        }

        public string AppearanceResult => "이상없음";
        public string AppearanceJudgment => "P";

        public string PrintStateResult => IsPrintedProduct ? "이상없음" : "-";
        public string PrintStateJudgment => IsPrintedProduct ? "P" : "-";

        public string PrintTypeText =>
            IsPrintedProduct
                ? "인쇄제품"
                : "무지제품";

        public string DimensionWidthCriteria
        {
            get => _dimensionWidthCriteria;
            set => SetProperty(ref _dimensionWidthCriteria, value);
        }

        public string DimensionHeightCriteria
        {
            get => _dimensionHeightCriteria;
            set => SetProperty(ref _dimensionHeightCriteria, value);
        }

        public string DimensionWidthResult
        {
            get => _dimensionWidthResult;
            set => SetProperty(ref _dimensionWidthResult, value);
        }

        public string DimensionHeightResult
        {
            get => _dimensionHeightResult;
            set => SetProperty(ref _dimensionHeightResult, value);
        }

        public string InspectionDateText =>
            Edit.InspectionDateSnapshot.HasValue
                ? Edit.InspectionDateSnapshot.Value.ToString("yyyy-MM-dd")
                : "-";

        public string QuantityText =>
            Edit.QuantitySnapshot > 0
                ? $"{Edit.QuantitySnapshot:N0} EA"
                : "-";

        public string IssueDateYear => DateTime.Today.ToString("yyyy");
        public string IssueDateMonth => DateTime.Today.ToString("MM");
        public string IssueDateDay => DateTime.Today.ToString("dd");

        public async Task InitializeAsync(long orderLineId)
        {
            _orderLineId = orderLineId;

            IsLoading = true;

            try
            {
                var result = await _apiClient.GetAsync<ShipmentCoaDto>(
                    $"{ApiRoutes.Shipments}/{orderLineId}/coa");

                if (!result.Success || result.Data == null)
                {
                    Coa = null;
                    Edit.Clear();
                    _messageService.ShowError(result.Message ?? "COA 정보를 조회하지 못했습니다.");
                    return;
                }

                Coa = result.Data;
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task SaveAsync()
        {
            if (_orderLineId <= 0)
            {
                _messageService.ShowWarning("COA 대상 출고 정보를 확인할 수 없습니다.");
                return;
            }

            if (Edit.QuantitySnapshot <= 0)
            {
                _messageService.ShowWarning("수량은 1 이상이어야 합니다.");
                return;
            }

            if (!Edit.InspectionDateSnapshot.HasValue)
            {
                _messageService.ShowWarning("검사일자를 입력하세요.");
                return;
            }

            IsLoading = true;

            try
            {
                var request = new ShipmentCoaUpdateRequest
                {
                    QuantitySnapshot = Edit.QuantitySnapshot,
                    InspectionDateSnapshot = Edit.InspectionDateSnapshot.Value.ToString("yyyy-MM-dd"),
                    Memo = string.IsNullOrWhiteSpace(Edit.Memo) ? null : Edit.Memo.Trim()
                };

                var result = await _apiClient.PatchAsync<ShipmentCoaUpdateRequest, ShipmentCoaDto>(
                    $"{ApiRoutes.Shipments}/{_orderLineId}/coa",
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "COA 저장 중 오류가 발생했습니다.");
                    return;
                }

                Coa = result.Data;
                _messageService.ShowInfo("COA 정보가 저장되었습니다.");
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void ApplyCoaToDisplay()
        {
            if (Coa == null)
            {
                Edit.Clear();
                IsPrintedProduct = false;
                ApplyDimensionFromSpec(null);
            }
            else
            {
                Edit.LoadFromDto(Coa);
                IsPrintedProduct = Coa.IsPrintedProductSnapshot;
                ApplyDimensionFromSpec(Coa.ProductSpecSnapshot);
            }

            OnPropertyChanged(nameof(ProductName));
            OnPropertyChanged(nameof(ProductSpec));
            OnPropertyChanged(nameof(Material));
            OnPropertyChanged(nameof(PartnerName));
            OnPropertyChanged(nameof(LotNos));
            OnPropertyChanged(nameof(InspectionDateText));
            OnPropertyChanged(nameof(QuantityText));
            OnPropertyChanged(nameof(AppearanceResult));
            OnPropertyChanged(nameof(AppearanceJudgment));
            OnPropertyChanged(nameof(PrintStateResult));
            OnPropertyChanged(nameof(PrintStateJudgment));
            OnPropertyChanged(nameof(PrintTypeText));
        }

        private void ApplyDimensionFromSpec(string? productSpec)
        {
            var dimension = ParseDimension(productSpec);

            if (dimension.Width == "-")
            {
                DimensionWidthCriteria = "-";
                DimensionWidthResult = "-";
            }
            else
            {
                DimensionWidthCriteria = $"{dimension.Width} ± 1";
                DimensionWidthResult = dimension.Width;
            }

            if (dimension.Height == "-")
            {
                DimensionHeightCriteria = "-";
                DimensionHeightResult = "-";
            }
            else
            {
                DimensionHeightCriteria = $"{dimension.Height} ± 1";
                DimensionHeightResult = dimension.Height;
            }
        }

        private static (string Width, string Height) ParseDimension(string? productSpec)
        {
            if (string.IsNullOrWhiteSpace(productSpec))
            {
                return ("-", "-");
            }

            var normalized = productSpec
                .Trim()
                .ToUpperInvariant()
                .Replace("×", "X")
                .Replace("*", "X");

            var parts = normalized.Split('X', StringSplitOptions.RemoveEmptyEntries);

            if (parts.Length < 2)
            {
                return ("-", "-");
            }

            var width = ExtractNumberText(parts[0]);
            var height = ExtractNumberText(parts[1]);

            return (
                string.IsNullOrWhiteSpace(width) ? "-" : width,
                string.IsNullOrWhiteSpace(height) ? "-" : height
            );
        }

        private static string ExtractNumberText(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return string.Empty;
            }

            var match = Regex.Match(value, @"\d+(\.\d+)?");

            return match.Success
                ? match.Value
                : value.Trim();
        }

        private void OnEditPropertyChanged(object? sender, PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(ShipmentCoaEditModel.QuantitySnapshot))
            {
                OnPropertyChanged(nameof(QuantityText));
            }

            if (e.PropertyName == nameof(ShipmentCoaEditModel.InspectionDateSnapshot))
            {
                OnPropertyChanged(nameof(InspectionDateText));
            }
        }
    }
}