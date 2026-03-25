using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.Lots.Dtos;
using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Lots.ViewModels
{
    public class LotCreateWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private readonly IDrawingViewer _drawingViewer;
        private readonly IDrawingFileOpener _drawingFileOpener;

        private bool _isLoading;
        private long _orderLineId;
        private LotCreatePrimaryCandidateDto? _selectedPrimaryLot;

        public LotCreateWindowViewModel(
            IApiClient apiClient,
            IMessageService messageService,
            IDrawingViewer drawingViewer,
            IDrawingFileOpener drawingFileOpener)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            _drawingViewer = drawingViewer;
            _drawingFileOpener = drawingFileOpener;

            EditModel = new LotCreateEditModel();
            PrimaryLots = new ObservableCollection<LotCreatePrimaryCandidateDto>();

            SaveCommand = new AsyncRelayCommand(SaveAsync);
            ResetCommand = new RelayCommand(ResetInputFields);
            ToggleReworkCommand = new RelayCommand(HandleReworkToggle);
        }

        public LotCreateEditModel EditModel { get; }

        public ObservableCollection<LotCreatePrimaryCandidateDto> PrimaryLots { get; }

        public AsyncRelayCommand SaveCommand { get; }

        public RelayCommand ResetCommand { get; }

        public RelayCommand ToggleReworkCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public LotCreatePrimaryCandidateDto? SelectedPrimaryLot
        {
            get => _selectedPrimaryLot;
            set
            {
                if (SetProperty(ref _selectedPrimaryLot, value))
                {
                    EditModel.ApplyParentLot(value);
                }
            }
        }

        public async Task InitializeAsync(long orderLineId)
        {
            _orderLineId = orderLineId;
            await LoadContextAsync();
        }

        private async Task LoadContextAsync()
        {
            EditModel.Clear();
            PrimaryLots.Clear();
            SelectedPrimaryLot = null;

            if (_orderLineId <= 0)
            {
                _messageService.ShowWarning("유효한 OrderLine 정보가 없습니다.");
                return;
            }

            IsLoading = true;
            try
            {
                var result = await _apiClient.GetAsync<LotCreateContextDto>(
                    $"{ApiRoutes.OrderLines}/{_orderLineId}/lot-create-context");

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "LOT 생성 정보 조회 중 오류가 발생했습니다.");
                    return;
                }

                ApplyContext(result.Data);
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void ApplyContext(LotCreateContextDto dto)
        {
            EditModel.LoadFromContext(dto);

            foreach (var item in dto.PrimaryLotCandidates.OrderByDescending(x => x.LotId))
            {
                PrimaryLots.Add(item);
            }
        }

        private void HandleReworkToggle()
        {
            if (!EditModel.IsRework)
            {
                SelectedPrimaryLot = null;
                EditModel.ApplyParentLot(null);
            }
        }

        private void ResetInputFields()
        {
            EditModel.IsRework = false;
            SelectedPrimaryLot = null;
            EditModel.ApplyParentLot(null);

            EditModel.MaterialLotNo = string.Empty;
            EditModel.MaterialUsedQty = null;
            EditModel.MaterialSheetCount = null;
            EditModel.PlanQty = EditModel.OrderQty;
            EditModel.Memo = null;
        }

        private void Normalize()
        {
            EditModel.Status = EditModel.Status?.Trim().ToUpperInvariant() ?? string.Empty;
            EditModel.ParentLotStatus = EditModel.ParentLotStatus?.Trim().ToUpperInvariant() ?? string.Empty;
            EditModel.ProductCode = EditModel.ProductCode?.Trim().ToUpperInvariant() ?? string.Empty;
            EditModel.Uom = EditModel.Uom?.Trim().ToUpperInvariant() ?? string.Empty;
            EditModel.MaterialLotNo = EditModel.MaterialLotNo?.Trim().ToUpperInvariant() ?? string.Empty;
            EditModel.Memo = EditModel.Memo?.Trim();
        }

        private bool Validate()
        {
            if (EditModel.OrderLineId <= 0)
            {
                _messageService.ShowWarning("수주라인 정보가 없습니다.");
                return false;
            }

            if (!string.Equals(EditModel.Status, "OPEN", StringComparison.OrdinalIgnoreCase))
            {
                _messageService.ShowWarning("LOT 생성은 OPEN 상태의 수주라인에서만 가능합니다.");
                return false;
            }

            if (!EditModel.PlanQty.HasValue || EditModel.PlanQty.Value <= 0)
            {
                _messageService.ShowWarning("계획수량은 1 이상이어야 합니다.");
                return false;
            }

            var hasMaterialLotNo = !string.IsNullOrWhiteSpace(EditModel.MaterialLotNo);
            var hasMaterialUsedQty = EditModel.MaterialUsedQty.HasValue;
            var hasMaterialSheetCount = EditModel.MaterialSheetCount.HasValue;

            if (hasMaterialLotNo && (!hasMaterialUsedQty || EditModel.MaterialUsedQty!.Value <= 0))
            {
                _messageService.ShowWarning("원단 LOT를 입력한 경우 원단 사용량은 0보다 커야 합니다.");
                return false;
            }

            if (hasMaterialUsedQty && !hasMaterialLotNo)
            {
                _messageService.ShowWarning("원단 사용량을 입력한 경우 원단 LOT가 필요합니다.");
                return false;
            }


            if (hasMaterialSheetCount && EditModel.MaterialSheetCount.Value <= 0)
            {
                _messageService.ShowWarning("시트수는 1 이상이어야 합니다.");
                return false;
            }

            if (hasMaterialSheetCount && !hasMaterialLotNo)
            {
                _messageService.ShowWarning("시트수를 입력한 경우 원단 LOT가 필요합니다.");
                return false;
            }




            if (!EditModel.IsRework)
            {
                return true;
            }

            if (SelectedPrimaryLot == null)
            {
                _messageService.ShowWarning("재작업 LOT는 부모 Primary LOT를 선택해야 합니다.");
                return false;
            }

            if (!SelectedPrimaryLot.CanCreateRework)
            {
                _messageService.ShowWarning("재작업 LOT는 부모 LOT가 DONE 또는 CANCELED일 때만 생성 가능합니다.");
                return false;
            }

            return true;
        }

        public async Task OpenDrawingFileAsync()
        {
            if (!EditModel.DrawingId.HasValue || EditModel.DrawingId.Value <= 0)
            {
                _messageService.ShowWarning("열 수 있는 도면 정보가 없습니다.");
                return;
            }

            await _drawingViewer.OpenCurrentDrawingAsync(EditModel.DrawingId.Value);
        }

        public async Task OpenOriginalFileAsync()
        {
            if (!EditModel.OriginalFileId.HasValue || EditModel.OriginalFileId.Value <= 0)
            {
                _messageService.ShowWarning("열 수 있는 원본 파일이 없습니다.");
                return;
            }

            var url = _apiClient.BuildAbsoluteUrl(
                $"{ApiRoutes.Drawings}/revision-files/{EditModel.OriginalFileId.Value}/download");

            await _drawingFileOpener.OpenRevisionFileAsync(
                url,
                string.IsNullOrWhiteSpace(EditModel.OriginalFileName) ? null : EditModel.OriginalFileName);
        }

        public async Task OpenPlateWorkAsync()
        {
            if (!EditModel.PlateFileId.HasValue || EditModel.PlateFileId.Value <= 0)
            {
                _messageService.ShowWarning("열 수 있는 판작업 파일이 없습니다.");
                return;
            }

            var url = _apiClient.BuildAbsoluteUrl(
                $"{ApiRoutes.Drawings}/revision-files/{EditModel.PlateFileId.Value}/download");

            await _drawingFileOpener.OpenRevisionFileAsync(
                url,
                string.IsNullOrWhiteSpace(EditModel.PlateFileName) ? null : EditModel.PlateFileName);
        }

        public async Task SaveAsync()
        {
            Normalize();

            if (!Validate())
            {
                return;
            }

            var confirmed = _messageService.Confirm("LOT를 생성하시겠습니까?", "LOT 생성");
            if (!confirmed)
            {
                return;
            }

            var request = new LotCreateRequest
            {
                OrderLineId = EditModel.OrderLineId,
                ParentLotId = EditModel.IsRework ? EditModel.ParentLotId : null,
                LotQty = EditModel.PlanQty ?? 0,
                CreatedDate = DateTime.Today,
                Memo = string.IsNullOrWhiteSpace(EditModel.Memo) ? null : EditModel.Memo,
                MaterialLotNo = string.IsNullOrWhiteSpace(EditModel.MaterialLotNo) ? null : EditModel.MaterialLotNo,
                MaterialUsedQty = EditModel.MaterialUsedQty,
                MaterialSheetCount = EditModel.MaterialSheetCount
            };

            IsLoading = true;
            try
            {
                var result = await _apiClient.PostAsync<LotCreateRequest, LotDto>(
                    ApiRoutes.Lots,
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "LOT 생성 중 오류가 발생했습니다.");
                    return;
                }

                _messageService.ShowInfo($"LOT가 생성되었습니다. [{result.Data.LotNo}]");

                await LoadContextAsync();
                ResetInputFields();
            }
            finally
            {
                IsLoading = false;
            }
        }
    }
}