using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OrderLines.Dtos;
using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.OrderLines.ViewModels
{
    public class OrderLineCreatePageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly IDrawingViewer _drawingViewer;

        private bool _isLoading;

        public OrderLineCreatePageViewModel(IApiClient apiClient, IMessageService messageService, IDrawingViewer drawingViewer)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _drawingViewer = drawingViewer;

            Header = new OrderLineCreateHeaderEditModel();
            Lines = new ObservableCollection<OrderLineCreateLineEditModel>();

            AddLineCommand = new RelayCommand(AddLine);
            ResetCommand = new RelayCommand(Reset);
            SaveCommand = new AsyncRelayCommand(SaveAsync);
        }

        public OrderLineCreateHeaderEditModel Header { get; }
        public ObservableCollection<OrderLineCreateLineEditModel> Lines { get; }

        public RelayCommand AddLineCommand { get; }
        public RelayCommand ResetCommand { get; }
        public AsyncRelayCommand SaveCommand { get; }

        public IApiClient ApiClient => _apiClient;
        public IMessageService MessageService => _messageService;

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public int TotalLineCount => Lines.Count;
        public int TotalOrderQty => Lines.Sum(x => x.OrderQty);

        public Task InitializeAsync()
        {
            Reset();
            return Task.CompletedTask;
        }

        public void ApplySelectedPartner(OrderLinePartnerLookupDto partner)
        {
            Header.PartnerId = partner.PartnerId;
            Header.PartnerName = partner.Name;
        }

        public void ApplySelectedProduct(OrderLineCreateLineEditModel line, OrderLineProductLookupDto product)
        {
            line.ApplyProduct(product);
            RefreshSummary();
        }

        public void AddLine()
        {
            Lines.Add(new OrderLineCreateLineEditModel
            {
                LineNo = Lines.Count + 1,
                OrderQty = 0
            });

            RefreshSummary();
        }

        public void RemoveLine(OrderLineCreateLineEditModel? line)
        {
            if (line == null)
            {
                return;
            }

            Lines.Remove(line);
            ResequenceLineNo();
            RefreshSummary();
        }

        private async Task SaveAsync()
        {
            Normalize();

            if (!ValidateForSave())
            {
                return;
            }

            var confirmed = _messageService.Confirm("현재 수주를 저장하시겠습니까?", "수주 저장");
            if (!confirmed)
            {
                return;
            }

            IsLoading = true;
            try
            {
                var currentLineNo = 1;

                foreach (var line in Lines)
                {
                    var request = new OrderLineCreateRequest
                    {
                        OrderNo = Header.OrderNo,
                        LineNo = currentLineNo,
                        PartnerId = Header.PartnerId!.Value,
                        ProductId = line.ProductId!.Value,
                        OrderDate = Header.OrderDate.Date,
                        DueDate = Header.DueDate.Date,
                        OrderQty = line.OrderQty,
                        Uom = line.Uom,
                        CustomerPo = null,
                        Memo = string.IsNullOrWhiteSpace(line.Memo) ? null : line.Memo
                    };

                    var result = await _apiClient.PostAsync<OrderLineCreateRequest, OrderLineDto>(
                        ApiRoutes.OrderLines,
                        request);

                    if (!result.Success || result.Data == null)
                    {
                        _messageService.ShowError(result.Message ?? $"라인 {currentLineNo} 저장 중 오류가 발생했습니다.");
                        return;
                    }

                    currentLineNo++;
                }

                _messageService.ShowInfo("수주가 저장되었습니다.");
                Reset();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void Reset()
        {
            Header.Clear();

            Lines.Clear();
            Lines.Add(new OrderLineCreateLineEditModel
            {
                LineNo = 1,
                OrderQty = 0
            });

            RefreshSummary();
        }

        private void Normalize()
        {
            Header.OrderNo = Header.OrderNo?.Trim().ToUpperInvariant() ?? string.Empty;
            Header.PartnerName = Header.PartnerName?.Trim() ?? string.Empty;

            foreach (var line in Lines)
            {
                line.ProductCode = line.ProductCode?.Trim().ToUpperInvariant() ?? string.Empty;
                line.ProductName = line.ProductName?.Trim() ?? string.Empty;
                line.ProductSpec = line.ProductSpec?.Trim() ?? string.Empty;
                line.Uom = line.Uom?.Trim().ToUpperInvariant() ?? string.Empty;
                line.Memo = line.Memo?.Trim();
            }
        }

        private bool ValidateForSave()
        {
            if (string.IsNullOrWhiteSpace(Header.OrderNo))
            {
                _messageService.ShowWarning("수주번호는 필수입니다.");
                return false;
            }

            if (!Header.PartnerId.HasValue)
            {
                _messageService.ShowWarning("거래처를 선택하세요.");
                return false;
            }

            if (Header.DueDate.Date < Header.OrderDate.Date)
            {
                _messageService.ShowWarning("납기일은 수주일자보다 빠를 수 없습니다.");
                return false;
            }

            if (Lines.Count == 0)
            {
                _messageService.ShowWarning("수주 라인을 1건 이상 입력하세요.");
                return false;
            }

            foreach (var line in Lines)
            {
                if (!line.ProductId.HasValue)
                {
                    _messageService.ShowWarning($"라인 {line.LineNo}: 품목을 선택하세요.");
                    return false;
                }

                if (line.OrderQty <= 0)
                {
                    _messageService.ShowWarning($"라인 {line.LineNo}: 수주수량은 1 이상이어야 합니다.");
                    return false;
                }

                if (string.IsNullOrWhiteSpace(line.Uom))
                {
                    _messageService.ShowWarning($"라인 {line.LineNo}: 단위 정보가 없습니다.");
                    return false;
                }
            }

            return true;
        }

        private void ResequenceLineNo()
        {
            for (int i = 0; i < Lines.Count; i++)
            {
                Lines[i].LineNo = i + 1;
            }
        }

        public void RefreshSummary()
        {
            OnPropertyChanged(nameof(TotalLineCount));
            OnPropertyChanged(nameof(TotalOrderQty));
        }

        public async Task ViewDrawingAsync(OrderLineCreateLineEditModel? line)
        {
            if (line == null || !line.DrawingId.HasValue || line.DrawingId.Value <= 0)
            {
                _messageService.ShowWarning("열 수 있는 도면 정보가 없습니다.");
                return;
            }

            await _drawingViewer.OpenCurrentDrawingAsync(line.DrawingId.Value);
        }
    }
}