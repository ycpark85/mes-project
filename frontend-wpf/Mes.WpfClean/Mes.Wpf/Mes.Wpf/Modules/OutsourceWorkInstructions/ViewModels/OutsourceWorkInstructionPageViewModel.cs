using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels
{
    public class OutsourceWorkInstructionPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private OutsourceWorkInstructionDraftEditModel? _selectedDraft;

        public OutsourceWorkInstructionPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            CandidateLots = new ObservableCollection<OutsourceWorkInstructionCandidateLotRowModel>();
            Drafts = new ObservableCollection<OutsourceWorkInstructionDraftEditModel>();

            AddDraftCommand = new RelayCommand(AddDraft);
            RemoveDraftCommand = new RelayCommand(RemoveDraft);
            UploadFileCommand = new AsyncRelayCommand(UploadFileAsync);
            SaveCommand = new AsyncRelayCommand(SaveAsync);
            ResetCommand = new AsyncRelayCommand(ResetAsync);
        }

        public ObservableCollection<OutsourceWorkInstructionCandidateLotRowModel> CandidateLots { get; }

        public ObservableCollection<OutsourceWorkInstructionDraftEditModel> Drafts { get; }

        public RelayCommand AddDraftCommand { get; }

        public RelayCommand RemoveDraftCommand { get; }

        public AsyncRelayCommand UploadFileCommand { get; }

        public AsyncRelayCommand SaveCommand { get; }

        public AsyncRelayCommand ResetCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public OutsourceWorkInstructionDraftEditModel? SelectedDraft
        {
            get => _selectedDraft;
            set => SetProperty(ref _selectedDraft, value);
        }

        public async Task InitializeAsync()
        {
            await LoadCandidatesAsync();
        }

        private async Task LoadCandidatesAsync()
        {
            IsLoading = true;

            try
            {
                var result = await _apiClient.GetAsync<OutsourceWorkInstructionCandidateLotListDto>(
                    ApiRoutes.OutsourceWorkInstructionCandidates);

                if (!result.Success || result.Data == null)
                {
                    CandidateLots.Clear();
                    _messageService.ShowError(result.Message ?? "후보 LOT 조회 중 오류가 발생했습니다.");
                    return;
                }

                CandidateLots.Clear();

                foreach (var item in result.Data.Items)
                {
                    CandidateLots.Add(OutsourceWorkInstructionCandidateLotRowModel.FromDto(item));
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void AddDraft()
        {
            var selectedLots = CandidateLots.Where(x => x.IsSelected).ToList();
            if (selectedLots.Count == 0)
            {
                _messageService.ShowWarning("작업지시에 추가할 LOT를 선택하세요.");
                return;
            }

            var firstPartnerId = selectedLots[0].CustomerPartnerId;
            if (selectedLots.Any(x => x.CustomerPartnerId != firstPartnerId))
            {
                _messageService.ShowWarning("같은 거래처 기준 LOT만 묶을 수 있습니다.");
                return;
            }

            var draft = new OutsourceWorkInstructionDraftEditModel
            {
                InstructionDate = DateTime.Today,
                CustomerPartnerId = selectedLots[0].CustomerPartnerId,
                CustomerPartnerName = selectedLots[0].CustomerPartnerName ?? string.Empty,
                SheetQty = 1
            };

            foreach (var lot in selectedLots)
            {
                lot.IsSelected = false;
                lot.ManualCutsPerSheet = null;
                draft.Lots.Add(lot);
            }

            if (!draft.IsBundle)
            {
                draft.SheetCutCount = draft.FirstLot?.CutQtyPerPanel;
            }

            draft.RefreshDerivedValues();

            Drafts.Add(draft);
            SelectedDraft = draft;

            foreach (var lot in selectedLots)
            {
                CandidateLots.Remove(lot);
            }

            OnPropertyChanged(nameof(Drafts));
            OnPropertyChanged(nameof(SelectedDraft));
        }

        private void RemoveDraft()
        {
            if (SelectedDraft == null)
            {
                _messageService.ShowWarning("제거할 작업지시를 선택하세요.");
                return;
            }

            foreach (var lot in SelectedDraft.Lots)
            {
                lot.IsSelected = false;
                lot.ManualCutsPerSheet = null;
                CandidateLots.Add(lot);
            }

            Drafts.Remove(SelectedDraft);
            SelectedDraft = null;

            OnPropertyChanged(nameof(Drafts));
            OnPropertyChanged(nameof(SelectedDraft));
        }

        private async Task UploadFileAsync()
        {
            if (SelectedDraft == null)
            {
                _messageService.ShowWarning("파일을 첨부할 작업지시를 선택하세요.");
                return;
            }

            var dialog = new OpenFileDialog
            {
                Multiselect = !SelectedDraft.IsBundle,
                Title = "판데이터 파일 선택"
            };

            if (dialog.ShowDialog() != true)
            {
                return;
            }

            if (SelectedDraft.IsBundle && dialog.FileNames.Length > 1)
            {
                _messageService.ShowWarning("묶음 작업지시는 판데이터 파일 1개만 첨부할 수 있습니다.");
                return;
            }

            foreach (var fileName in dialog.FileNames)
            {
                using var content = new MultipartFormDataContent();
                using var stream = File.OpenRead(fileName);
                using var fileContent = new StreamContent(stream);

                content.Add(fileContent, "file", Path.GetFileName(fileName));

                var upload = await _apiClient.PostMultipartAsync<OutsourceWorkInstructionUploadResultDto>(
                    ApiRoutes.OutsourceWorkInstructionPlateUpload,
                    content);

                if (!upload.Success || upload.Data == null)
                {
                    _messageService.ShowError(upload.Message ?? "파일 업로드 중 오류가 발생했습니다.");
                    return;
                }

                SelectedDraft.Files.Add(new OutsourceWorkInstructionFileCreateRequest
                {
                    FileName = upload.Data.FileName,
                    FilePath = upload.Data.FilePath,
                    ContentType = upload.Data.ContentType
                });
            }

            OnPropertyChanged(nameof(SelectedDraft));
        }

        private async Task SaveAsync()
        {
            if (Drafts.Count == 0)
            {
                _messageService.ShowWarning("저장할 작업지시가 없습니다.");
                return;
            }

            foreach (var draft in Drafts)
            {
                if (draft.IsBundle && draft.Files.Count == 0)
                {
                    _messageService.ShowWarning("묶음 작업지시는 판데이터 첨부가 필요합니다.");
                    return;
                }

                if (draft.IsBundle && draft.Files.Count > 1)
                {
                    _messageService.ShowWarning("묶음 작업지시는 판데이터 파일 1개만 첨부할 수 있습니다.");
                    return;
                }
            }

            var request = new OutsourceWorkInstructionBatchCreateRequest
            {
                InstructionDate = DateTime.Today
            };

            foreach (var draft in Drafts)
            {
                request.Groups.Add(new OutsourceWorkInstructionBatchGroupCreateRequest
                {
                    CustomerPartnerId = draft.CustomerPartnerId,
                    Memo = string.IsNullOrWhiteSpace(draft.Memo) ? null : draft.Memo.Trim(),
                    LotIds = draft.Lots.Select(x => x.LotId).ToList(),
                    Files = draft.Files.ToList(),
                    WorkGroups = BuildWorkGroups(draft)
                });
            }

            IsLoading = true;

            try
            {
                var result = await _apiClient.PostAsync<OutsourceWorkInstructionBatchCreateRequest, OutsourceWorkInstructionBatchResponseDto>(
                    ApiRoutes.OutsourceWorkInstructionBatch,
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "외주 작업지시 저장 중 오류가 발생했습니다.");
                    return;
                }

                Drafts.Clear();
                SelectedDraft = null;

                _messageService.ShowInfo("외주 작업지시가 일괄 저장되었습니다.");
                await LoadCandidatesAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        private List<OutsourceWorkInstructionGroupCreateRequest> BuildWorkGroups(OutsourceWorkInstructionDraftEditModel draft)
        {
            var groups = new List<OutsourceWorkInstructionGroupCreateRequest>();

            if (draft.Lots.Count == 0)
            {
                return groups;
            }

            var group = new OutsourceWorkInstructionGroupCreateRequest
            {
                GroupSeq = 1,
                IsBundle = draft.IsBundle,
                SheetQty = ResolveSheetQty(draft),
                LengthM = draft.LengthM,
                SheetCutCount = ResolveSheetCutCount(draft),
                Remark = string.IsNullOrWhiteSpace(draft.Memo) ? null : draft.Memo.Trim()
            };

            foreach (var lot in draft.Lots)
            {
                var cutsPerSheet = ResolveCutsPerSheet(draft, lot);

                group.Items.Add(new OutsourceWorkInstructionGroupItemCreateRequest
                {
                    LotId = lot.LotId,
                    CutsPerSheet = cutsPerSheet,
                    ExpectedOutputQty = ResolveExpectedOutputQty(draft, cutsPerSheet),
                    Remark = null
                });
            }

            groups.Add(group);
            return groups;
        }

        private int ResolveSheetQty(OutsourceWorkInstructionDraftEditModel draft)
        {
            return draft.SheetQty > 0 ? draft.SheetQty : 1;
        }

        private int? ResolveSheetCutCount(OutsourceWorkInstructionDraftEditModel draft)
        {
            if (!draft.IsBundle)
            {
                if (draft.FirstLot?.CutQtyPerPanel is int cutQtyPerPanel && cutQtyPerPanel > 0)
                {
                    return cutQtyPerPanel;
                }

                return draft.SheetCutCount.HasValue && draft.SheetCutCount.Value > 0
                    ? draft.SheetCutCount.Value
                    : null;
            }

            if (draft.SheetCutCount.HasValue && draft.SheetCutCount.Value > 0)
            {
                return draft.SheetCutCount.Value;
            }

            var manualSum = draft.Lots.Sum(x => x.ManualCutsPerSheet ?? 0);
            return manualSum > 0 ? manualSum : null;
        }

        private int ResolveCutsPerSheet(
            OutsourceWorkInstructionDraftEditModel draft,
            OutsourceWorkInstructionCandidateLotRowModel lot)
        {
            if (draft.IsBundle)
            {
                if (lot.ManualCutsPerSheet.HasValue && lot.ManualCutsPerSheet.Value > 0)
                {
                    return lot.ManualCutsPerSheet.Value;
                }

                if (lot.CutQtyPerPanel.HasValue && lot.CutQtyPerPanel.Value > 0)
                {
                    return lot.CutQtyPerPanel.Value;
                }

                return 1;
            }

            if (lot.CutQtyPerPanel.HasValue && lot.CutQtyPerPanel.Value > 0)
            {
                return lot.CutQtyPerPanel.Value;
            }

            return 1;
        }

        private int? ResolveExpectedOutputQty(OutsourceWorkInstructionDraftEditModel draft, int cutsPerSheet)
        {
            var sheetQty = ResolveSheetQty(draft);
            if (sheetQty <= 0 || cutsPerSheet <= 0)
            {
                return null;
            }

            return sheetQty * cutsPerSheet;
        }

        private async Task ResetAsync()
        {
            Drafts.Clear();
            SelectedDraft = null;
            await LoadCandidatesAsync();
        }
    }
}