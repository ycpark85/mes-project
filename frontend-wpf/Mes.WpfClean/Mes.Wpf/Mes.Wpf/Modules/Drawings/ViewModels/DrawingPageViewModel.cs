using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Common.ViewModels;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Core.Models;
using Mes.Wpf.Modules.Drawings.Dtos;
using Microsoft.Win32;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.Drawings.ViewModels
{
    public class DrawingPageViewModel : CrudPageViewModelBase<DrawingDto>
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _searchKeyword = string.Empty;
        private string _selectedUseYn = "사용";
        private bool _isCodeEditable = true;

        private bool _isEditMode;
        private bool _isNewMode;

        private DrawingRevisionDto? _selectedRevision;

        private string _drawingUploadPath = string.Empty;
        private string _originalUploadPath = string.Empty;
        private string _plateUploadPath = string.Empty;

        private bool _isDrawingFileDirty;
        private bool _isOriginalFileDirty;
        private bool _isPlateFileDirty;

        private string _loadingMessage = "처리 중입니다...";

        public DrawingPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<DrawingDto>();
            RevisionItems = new ObservableCollection<DrawingRevisionDto>();
            UseYnOptions = new ObservableCollection<string> { "사용", "미사용" };

            EditModel = new DrawingEditModel();
            RevisionEditModel = new DrawingRevisionEditModel();

            SaveCommand = new AsyncRelayCommand(SaveAsync);
            DeleteCommand = new AsyncRelayCommand(DeleteAsync);

            EditCommand = new RelayCommand(BeginEdit);
            CancelEditCommand = new RelayCommand(CancelEdit);

            NewRevisionCommand = new RelayCommand(NewRevision);

            CreateRevisionCommand = new AsyncRelayCommand(SaveRevisionBundleAsync);
            SaveRevisionBundleCommand = new AsyncRelayCommand(SaveRevisionBundleAsync);
            SetCurrentRevisionCommand = new AsyncRelayCommand(SetCurrentRevisionAsync);

            BrowseDrawingFileCommand = new RelayCommand(BrowseDrawingFile);
            BrowseOriginalFileCommand = new RelayCommand(BrowseOriginalFile);
            BrowsePlateFileCommand = new RelayCommand(BrowsePlateFile);

            UploadDrawingFileCommand = new AsyncRelayCommand(UploadDrawingFileAsync);
            UploadOriginalFileCommand = new AsyncRelayCommand(UploadOriginalFileAsync);
            UploadPlateFileCommand = new AsyncRelayCommand(UploadPlateFileAsync);

            ReplaceDrawingFileCommand = new AsyncRelayCommand(ReplaceDrawingFileAsync);
            ReplaceOriginalFileCommand = new AsyncRelayCommand(ReplaceOriginalFileAsync);
            ReplacePlateFileCommand = new AsyncRelayCommand(ReplacePlateFileAsync);

            SaveChangedFilesCommand = new AsyncRelayCommand(SaveChangedFilesAsync);

            OpenDrawingFileCommand = new RelayCommand(() => _ = OpenDrawingFileAsync());
            OpenOriginalFileCommand = new RelayCommand(() => _ = OpenOriginalFileAsync());
            OpenPlateFileCommand = new RelayCommand(() => _ = OpenPlateFileAsync());
        }

        public ObservableCollection<DrawingDto> Items { get; }
        public ObservableCollection<DrawingRevisionDto> RevisionItems { get; }
        public ObservableCollection<string> UseYnOptions { get; }

        public DrawingEditModel EditModel { get; }
        public DrawingRevisionEditModel RevisionEditModel { get; }

        public AsyncRelayCommand SaveCommand { get; }
        public AsyncRelayCommand DeleteCommand { get; }

        public RelayCommand EditCommand { get; }
        public RelayCommand CancelEditCommand { get; }

        public AsyncRelayCommand CreateRevisionCommand { get; }
        public AsyncRelayCommand SaveRevisionBundleCommand { get; }
        public AsyncRelayCommand SetCurrentRevisionCommand { get; }

        public RelayCommand BrowseDrawingFileCommand { get; }
        public RelayCommand BrowseOriginalFileCommand { get; }
        public RelayCommand BrowsePlateFileCommand { get; }

        public AsyncRelayCommand UploadDrawingFileCommand { get; }
        public AsyncRelayCommand UploadOriginalFileCommand { get; }
        public AsyncRelayCommand UploadPlateFileCommand { get; }

        public AsyncRelayCommand ReplaceDrawingFileCommand { get; }
        public AsyncRelayCommand ReplaceOriginalFileCommand { get; }
        public AsyncRelayCommand ReplacePlateFileCommand { get; }

        public AsyncRelayCommand SaveChangedFilesCommand { get; }

        public RelayCommand OpenDrawingFileCommand { get; }
        public RelayCommand OpenOriginalFileCommand { get; }
        public RelayCommand OpenPlateFileCommand { get; }

        public RelayCommand NewRevisionCommand { get; }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public string SelectedUseYn
        {
            get => _selectedUseYn;
            set => SetProperty(ref _selectedUseYn, value);
        }

        public bool IsCodeEditable
        {
            get => _isCodeEditable;
            set => SetProperty(ref _isCodeEditable, value);
        }

        public bool IsEditMode
        {
            get => _isEditMode;
            set => SetProperty(ref _isEditMode, value);
        }

        public bool IsNewMode
        {
            get => _isNewMode;
            set => SetProperty(ref _isNewMode, value);
        }

        public DrawingRevisionDto? SelectedRevision
        {
            get => _selectedRevision;
            set
            {
                if (SetProperty(ref _selectedRevision, value))
                {
                    LoadRevisionToEditModel(value);
                }
            }
        }

        public string DrawingUploadPath
        {
            get => _drawingUploadPath;
            set
            {
                if (SetProperty(ref _drawingUploadPath, value))
                {
                    IsDrawingFileDirty = !string.IsNullOrWhiteSpace(value);
                    OnPropertyChanged(nameof(DrawingUploadFileName));
                    OnPropertyChanged(nameof(DrawingDisplayFileName));
                    OnPropertyChanged(nameof(CanSaveChangedFiles));
                }
            }
        }

        public string OriginalUploadPath
        {
            get => _originalUploadPath;
            set
            {
                if (SetProperty(ref _originalUploadPath, value))
                {
                    IsOriginalFileDirty = !string.IsNullOrWhiteSpace(value);
                    OnPropertyChanged(nameof(OriginalUploadFileName));
                    OnPropertyChanged(nameof(OriginalDisplayFileName));
                    OnPropertyChanged(nameof(CanSaveChangedFiles));
                }
            }
        }

        public string PlateUploadPath
        {
            get => _plateUploadPath;
            set
            {
                if (SetProperty(ref _plateUploadPath, value))
                {
                    IsPlateFileDirty = !string.IsNullOrWhiteSpace(value);
                    OnPropertyChanged(nameof(PlateUploadFileName));
                    OnPropertyChanged(nameof(PlateDisplayFileName));
                    OnPropertyChanged(nameof(CanSaveChangedFiles));
                }
            }
        }

        public bool IsDrawingFileDirty
        {
            get => _isDrawingFileDirty;
            set => SetProperty(ref _isDrawingFileDirty, value);
        }

        public bool IsOriginalFileDirty
        {
            get => _isOriginalFileDirty;
            set => SetProperty(ref _isOriginalFileDirty, value);
        }

        public bool IsPlateFileDirty
        {
            get => _isPlateFileDirty;
            set => SetProperty(ref _isPlateFileDirty, value);
        }

        public string DrawingUploadFileName =>
            string.IsNullOrWhiteSpace(DrawingUploadPath) ? string.Empty : Path.GetFileName(DrawingUploadPath);

        public string OriginalUploadFileName =>
            string.IsNullOrWhiteSpace(OriginalUploadPath) ? string.Empty : Path.GetFileName(OriginalUploadPath);

        public string PlateUploadFileName =>
            string.IsNullOrWhiteSpace(PlateUploadPath) ? string.Empty : Path.GetFileName(PlateUploadPath);

        public string DrawingDisplayFileName =>
            !string.IsNullOrWhiteSpace(DrawingUploadFileName)
                ? DrawingUploadFileName
                : RevisionEditModel.DrawingFileName;

        public string OriginalDisplayFileName =>
            !string.IsNullOrWhiteSpace(OriginalUploadFileName)
                ? OriginalUploadFileName
                : RevisionEditModel.OriginalFileName;

        public string PlateDisplayFileName =>
            !string.IsNullOrWhiteSpace(PlateUploadFileName)
                ? PlateUploadFileName
                : RevisionEditModel.PlateFileName;

        public string LoadingMessage
        {
            get => _loadingMessage;
            set => SetProperty(ref _loadingMessage, value);
        }

        public bool IsRevisionSectionEnabled => EditModel.DrawingId.HasValue;
        public bool CanCreateRevision => EditModel.DrawingId.HasValue;
        public bool CanManageRevisionFiles => RevisionEditModel.RevisionId.HasValue;

        public bool CanSaveChangedFiles =>
            RevisionEditModel.RevisionId.HasValue &&
            (
                (IsDrawingFileDirty && !string.IsNullOrWhiteSpace(DrawingUploadPath)) ||
                (IsOriginalFileDirty && !string.IsNullOrWhiteSpace(OriginalUploadPath)) ||
                (IsPlateFileDirty && !string.IsNullOrWhiteSpace(PlateUploadPath))
            );

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        protected override async Task LoadListAsync()
        {
            var route = BuildListUrl();
            var result = await _apiClient.GetAsync<PagedResult<DrawingDto>>(route);

            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "도면 조회 중 오류가 발생했습니다.");
                return;
            }

            Items.Clear();
            foreach (var item in result.Data?.Items ?? new List<DrawingDto>())
            {
                Items.Add(item);
            }
        }

        protected override void Reset()
        {
            SearchKeyword = string.Empty;
            SelectedUseYn = "사용";

            SelectedItem = null;
            SelectedRevision = null;

            EditModel.Clear();
            RevisionEditModel.Clear();
            RevisionItems.Clear();
            ClearUploadPaths();
            ClearDirtyFlags();

            IsCodeEditable = true;
            IsEditMode = false;
            IsNewMode = false;
            LoadingMessage = "처리 중입니다...";

            RaiseAllStates();
        }

        protected override void New()
        {
            SelectedItem = null;
            SelectedRevision = null;

            EditModel.Clear();
            RevisionEditModel.Clear();
            RevisionItems.Clear();
            ClearUploadPaths();
            ClearDirtyFlags();

            IsCodeEditable = true;
            IsEditMode = true;
            IsNewMode = true;
            LoadingMessage = "처리 중입니다...";

            RaiseAllStates();
        }

        protected override void OnSelectedItemChanged(DrawingDto? item)
        {
            LoadToEditModel(item);

            IsEditMode = false;
            IsNewMode = false;

            if (item == null)
            {
                RevisionItems.Clear();
                RevisionEditModel.Clear();
                ClearUploadPaths();
                ClearDirtyFlags();
                RaiseAllStates();
                return;
            }

            _ = LoadRevisionListAsync(item.DrawingId);
            RaiseAllStates();
        }

        private void BeginEdit()
        {
            if (SelectedItem == null || !EditModel.DrawingId.HasValue)
            {
                _messageService.ShowWarning("수정할 도면을 선택하세요.");
                return;
            }

            IsEditMode = true;
            IsNewMode = false;
            IsCodeEditable = true;
        }

        private void CancelEdit()
        {
            if (SelectedItem == null)
            {
                EditModel.Clear();
                IsCodeEditable = true;
                IsEditMode = false;
                IsNewMode = false;
                RaiseAllStates();
                return;
            }

            LoadToEditModel(SelectedItem);
            IsEditMode = false;
            IsNewMode = false;
            RaiseAllStates();
        }

        private async Task SaveAsync()
        {
            NormalizeEditModel();

            if (!ValidateForSave())
                return;

            if (!IsNewMode && !IsEditMode)
            {
                _messageService.ShowWarning("신규 또는 수정 상태에서만 저장할 수 있습니다.");
                return;
            }

            IsLoading = true;
            LoadingMessage = "도면 저장 중...";
            await Task.Yield();

            string? successMessage = null;

            try
            {
                if (IsNewMode || !EditModel.DrawingId.HasValue)
                    successMessage = await CreateAsync();
                else
                    successMessage = await UpdateAsync(EditModel.DrawingId.Value);
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (!string.IsNullOrWhiteSpace(successMessage))
            {
                _messageService.ShowInfo(successMessage);
            }
        }

        private async Task DeleteAsync()
        {
            if (SelectedItem == null || !EditModel.DrawingId.HasValue)
            {
                _messageService.ShowWarning("삭제할 항목을 먼저 선택하세요.");
                return;
            }

            if (!EditModel.IsActive)
            {
                _messageService.ShowWarning("이미 미사용 처리된 도면입니다.");
                return;
            }

            var confirmed = _messageService.Confirm(
                $"[{SelectedItem.DrawingNo}] 도면을 삭제하시겠습니까?",
                "삭제 확인");

            if (!confirmed)
                return;

            IsLoading = true;
            LoadingMessage = "도면 삭제 중...";
            await Task.Yield();

            var deleted = false;

            try
            {
                var result = await _apiClient.DeleteAsync($"{ApiRoutes.Drawings}/{SelectedItem.DrawingId}");
                if (!result.Success || !result.Data)
                {
                    _messageService.ShowError(result.Message ?? "도면 삭제 중 오류가 발생했습니다.");
                    return;
                }

                await SearchAsync();

                SelectedItem = null;
                SelectedRevision = null;
                EditModel.Clear();
                RevisionEditModel.Clear();
                RevisionItems.Clear();
                ClearUploadPaths();
                ClearDirtyFlags();

                IsCodeEditable = true;
                IsEditMode = false;
                IsNewMode = false;

                RaiseAllStates();

                deleted = true;
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (deleted)
            {
                _messageService.ShowInfo("삭제되었습니다.");
            }
        }

        private async Task<string?> CreateAsync()
        {
            var request = new DrawingCreateRequest
            {
                DrawingNo = EditModel.DrawingNo,
                IsActive = EditModel.IsActive
            };

            var result = await _apiClient.PostAsync<DrawingCreateRequest, DrawingDto>(
                ApiRoutes.Drawings,
                request);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "도면 저장 중 오류가 발생했습니다.");
                return null;
            }

            await SearchAsync();

            SelectedItem = Items.FirstOrDefault(x => x.DrawingId == result.Data.DrawingId) ?? result.Data;
            LoadToEditModel(result.Data);

            IsCodeEditable = false;
            IsEditMode = false;
            IsNewMode = false;

            RaiseAllStates();

            return "저장되었습니다.";
        }

        private async Task<string?> UpdateAsync(long drawingId)
        {
            var request = new DrawingUpdateRequest
            {
                DrawingNo = EditModel.DrawingNo,
                IsActive = EditModel.IsActive
            };

            var result = await _apiClient.PatchAsync<DrawingUpdateRequest, DrawingDto>(
                $"{ApiRoutes.Drawings}/{drawingId}",
                request);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "도면 수정 중 오류가 발생했습니다.");
                return null;
            }

            await SearchAsync();

            SelectedItem = Items.FirstOrDefault(x => x.DrawingId == drawingId) ?? result.Data;
            LoadToEditModel(result.Data);

            IsCodeEditable = false;
            IsEditMode = false;
            IsNewMode = false;

            RaiseAllStates();

            return "저장되었습니다.";
        }

        private async Task LoadRevisionListAsync(long drawingId)
        {
            var route = $"{ApiRoutes.Drawings}/{drawingId}/revisions?page=1&size=100";
            var result = await _apiClient.GetAsync<PagedResult<DrawingRevisionDto>>(route);

            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "리비전 조회 중 오류가 발생했습니다.");
                return;
            }

            var currentSelectedRevisionId = SelectedRevision?.RevisionId ?? RevisionEditModel.RevisionId;

            RevisionItems.Clear();
            foreach (var item in result.Data?.Items ?? new List<DrawingRevisionDto>())
            {
                RevisionItems.Add(item);
            }

            if (currentSelectedRevisionId.HasValue)
            {
                SelectedRevision = RevisionItems.FirstOrDefault(x => x.RevisionId == currentSelectedRevisionId.Value);
            }
        }

        private async Task SaveRevisionBundleAsync()
        {
            if (!EditModel.DrawingId.HasValue)
            {
                _messageService.ShowWarning("먼저 도면을 저장하세요.");
                return;
            }

            // 이미 선택된 리비전이 있으면 신규 생성이 아니라 기존 리비전 선택 상태일 가능성이 큼
            // 이 버튼은 '신규 리비전 저장' 용도로만 사용
            if (RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("기존 리비전이 선택되어 있습니다. 신규 리비전을 저장하려면 리비전 관리에서 [신규]를 먼저 누르세요.");
                return;
            }

            RevisionEditModel.RevNo = RevisionEditModel.RevNo?.Trim() ?? string.Empty;

            if (string.IsNullOrWhiteSpace(RevisionEditModel.RevNo))
            {
                _messageService.ShowWarning("리비전 번호는 필수입니다.");
                return;
            }

            var drawingId = EditModel.DrawingId.Value;

            IsLoading = true;
            LoadingMessage = "리비전 저장 중...";
            await Task.Yield();

            var completed = false;

            try
            {
                var request = new DrawingRevisionCreateRequest
                {
                    RevNo = RevisionEditModel.RevNo,
                    SetAsCurrent = RevisionEditModel.SetAsCurrent
                };

                var result = await _apiClient.PostAsync<DrawingRevisionCreateRequest, DrawingRevisionDto>(
                    $"{ApiRoutes.Drawings}/{drawingId}/revisions",
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "리비전 생성 중 오류가 발생했습니다.");
                    return;
                }

                var createdRevision = result.Data;

                if (!string.IsNullOrWhiteSpace(DrawingUploadPath))
                {
                    var ok = await UploadRevisionFileInternalAsync(createdRevision.RevisionId, "DRAWING", DrawingUploadPath);
                    if (!ok) return;
                }

                if (!string.IsNullOrWhiteSpace(OriginalUploadPath))
                {
                    var ok = await UploadRevisionFileInternalAsync(createdRevision.RevisionId, "ORIGINAL", OriginalUploadPath);
                    if (!ok) return;
                }

                if (!string.IsNullOrWhiteSpace(PlateUploadPath))
                {
                    var ok = await UploadRevisionFileInternalAsync(createdRevision.RevisionId, "PLATE", PlateUploadPath);
                    if (!ok) return;
                }

                await LoadRevisionListAsync(drawingId);

                SelectedRevision = RevisionItems.FirstOrDefault(x => x.RevisionId == createdRevision.RevisionId);
                if (SelectedRevision != null)
                {
                    LoadRevisionToEditModel(SelectedRevision);
                }

                ClearUploadPaths();
                ClearDirtyFlags();

                completed = true;
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (completed)
            {
                _messageService.ShowInfo("리비전이 저장되었습니다.");
            }
        }

        private async Task SetCurrentRevisionAsync()
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("현재 리비전으로 지정할 항목을 선택하세요.");
                return;
            }

            var drawingId = EditModel.DrawingId.Value;
            var revisionId = RevisionEditModel.RevisionId.Value;

            IsLoading = true;
            LoadingMessage = "현재 리비전 지정 중...";
            await Task.Yield();

            var completed = false;

            try
            {
                var result = await _apiClient.PostAsync<object, DrawingRevisionDto>(
                    $"{ApiRoutes.Drawings}/{drawingId}/current-revision/{revisionId}",
                    new { });

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "현재 리비전 지정 중 오류가 발생했습니다.");
                    return;
                }

                await SearchAsync();
                await LoadRevisionListAsync(drawingId);

                SelectedItem = Items.FirstOrDefault(x => x.DrawingId == drawingId);
                if (SelectedItem != null)
                {
                    LoadToEditModel(SelectedItem);
                }

                SelectedRevision = RevisionItems.FirstOrDefault(x => x.RevisionId == revisionId);

                completed = true;
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (completed)
            {
                _messageService.ShowInfo("현재 리비전으로 지정되었습니다.");
            }
        }

        private async Task UploadDrawingFileAsync()
        {
            await UploadRevisionFileAsync("DRAWING", DrawingUploadPath);
        }

        private async Task UploadOriginalFileAsync()
        {
            await UploadRevisionFileAsync("ORIGINAL", OriginalUploadPath);
        }

        private async Task UploadPlateFileAsync()
        {
            await UploadRevisionFileAsync("PLATE", PlateUploadPath);
        }

        private async Task ReplaceDrawingFileAsync()
        {
            await ReplaceRevisionFileAsync("DRAWING", DrawingUploadPath);
        }

        private async Task ReplaceOriginalFileAsync()
        {
            await ReplaceRevisionFileAsync("ORIGINAL", OriginalUploadPath);
        }

        private async Task ReplacePlateFileAsync()
        {
            await ReplaceRevisionFileAsync("PLATE", PlateUploadPath);
        }

        private async Task SaveChangedFilesAsync()
        {
            if (!RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("먼저 리비전을 선택하세요.");
                return;
            }

            if (!CanSaveChangedFiles)
            {
                _messageService.ShowWarning("변경된 파일이 없습니다.");
                return;
            }

            IsLoading = true;
            LoadingMessage = "변경 파일 저장 중...";
            await Task.Yield();

            var completed = false;

            try
            {
                if (IsDrawingFileDirty && !string.IsNullOrWhiteSpace(DrawingUploadPath))
                {
                    var ok = await SaveChangedFileInternalAsync("DRAWING", DrawingUploadPath);
                    if (!ok) return;
                }

                if (IsOriginalFileDirty && !string.IsNullOrWhiteSpace(OriginalUploadPath))
                {
                    var ok = await SaveChangedFileInternalAsync("ORIGINAL", OriginalUploadPath);
                    if (!ok) return;
                }

                if (IsPlateFileDirty && !string.IsNullOrWhiteSpace(PlateUploadPath))
                {
                    var ok = await SaveChangedFileInternalAsync("PLATE", PlateUploadPath);
                    if (!ok) return;
                }

                await ReloadSelectedRevisionAsync();
                ClearUploadPaths();
                ClearDirtyFlags();

                completed = true;
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (completed)
            {
                _messageService.ShowInfo("변경된 파일이 저장되었습니다.");
            }
        }

        private async Task<bool> SaveChangedFileInternalAsync(string fileKind, string filePath)
        {
            if (HasRevisionFile(fileKind))
            {
                return await ReplaceRevisionFileInternalAsync(fileKind, filePath);
            }

            return await UploadRevisionFileInternalAsync(RevisionEditModel.RevisionId!.Value, fileKind, filePath);
        }

        private async Task UploadRevisionFileAsync(string fileKind, string filePath)
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("먼저 리비전을 선택하세요.");
                return;
            }

            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
            {
                _messageService.ShowWarning("업로드할 파일을 선택하세요.");
                return;
            }

            IsLoading = true;
            LoadingMessage = $"{GetFileKindDisplayName(fileKind)} 업로드 중...";
            await Task.Yield();

            var completed = false;

            try
            {
                completed = await UploadRevisionFileInternalAsync(RevisionEditModel.RevisionId.Value, fileKind, filePath);
                if (!completed) return;

                await ReloadSelectedRevisionAsync();
                ClearUploadPath(fileKind);
                ClearDirtyFlag(fileKind);
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (completed)
            {
                _messageService.ShowInfo("파일이 업로드되었습니다.");
            }
        }

        private async Task ReplaceRevisionFileAsync(string fileKind, string filePath)
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("먼저 리비전을 선택하세요.");
                return;
            }

            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
            {
                _messageService.ShowWarning("교체할 파일을 선택하세요.");
                return;
            }

            IsLoading = true;
            LoadingMessage = $"{GetFileKindDisplayName(fileKind)} 교체 중...";
            await Task.Yield();

            var completed = false;

            try
            {
                completed = await ReplaceRevisionFileInternalAsync(fileKind, filePath);
                if (!completed) return;

                await ReloadSelectedRevisionAsync();
                ClearUploadPath(fileKind);
                ClearDirtyFlag(fileKind);
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }

            if (completed)
            {
                _messageService.ShowInfo("파일이 교체되었습니다.");
            }
        }

        private async Task<bool> UploadRevisionFileInternalAsync(long revisionId, string fileKind, string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
            {
                _messageService.ShowWarning("업로드할 파일을 선택하세요.");
                return false;
            }

            using var content = BuildMultipartFileContent(fileKind, filePath, true);

            var result = await _apiClient.PostMultipartAsync<DrawingRevisionFileDto>(
                $"{ApiRoutes.Drawings}/{EditModel.DrawingId.Value}/revisions/{revisionId}/files",
                content);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? $"{GetFileKindDisplayName(fileKind)} 업로드 중 오류가 발생했습니다.");
                return false;
            }

            return true;
        }

        private async Task<bool> ReplaceRevisionFileInternalAsync(string fileKind, string filePath)
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("먼저 리비전을 선택하세요.");
                return false;
            }

            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
            {
                _messageService.ShowWarning("교체할 파일을 선택하세요.");
                return false;
            }

            using var content = BuildMultipartFileContent(fileKind, filePath, false);

            var result = await _apiClient.PatchMultipartAsync<DrawingRevisionFileDto>(
                $"{ApiRoutes.Drawings}/{EditModel.DrawingId.Value}/revisions/{RevisionEditModel.RevisionId.Value}/files/{fileKind}",
                content);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? $"{GetFileKindDisplayName(fileKind)} 교체 중 오류가 발생했습니다.");
                return false;
            }

            return true;
        }

        private async Task OpenDrawingFileAsync()
        {
            await OpenRevisionFileAsync(RevisionEditModel.DrawingFileId, RevisionEditModel.DrawingFileName);
        }

        private async Task OpenOriginalFileAsync()
        {
            await OpenRevisionFileAsync(RevisionEditModel.OriginalFileId, RevisionEditModel.OriginalFileName);
        }

        private async Task OpenPlateFileAsync()
        {
            await OpenRevisionFileAsync(RevisionEditModel.PlateFileId, RevisionEditModel.PlateFileName);
        }

        private async Task OpenRevisionFileAsync(long? revisionFileId, string? fileName)
        {
            if (!revisionFileId.HasValue)
            {
                _messageService.ShowWarning("열 수 있는 파일이 없습니다.");
                return;
            }

            var url = _apiClient.BuildAbsoluteUrl($"{ApiRoutes.Drawings}/revision-files/{revisionFileId.Value}/download");

            IsLoading = true;
            LoadingMessage = "파일 여는 중...";
            await Task.Yield();

            try
            {
                using var httpClient = new HttpClient();
                using var response = await httpClient.GetAsync(url);
                response.EnsureSuccessStatusCode();

                var bytes = await response.Content.ReadAsByteArrayAsync();

                var safeFileName = string.IsNullOrWhiteSpace(fileName)
                    ? $"drawing_file_{revisionFileId.Value}"
                    : fileName;

                var extension = Path.GetExtension(safeFileName);
                if (string.IsNullOrWhiteSpace(extension))
                {
                    var mediaType = response.Content.Headers.ContentType?.MediaType ?? string.Empty;

                    extension = mediaType switch
                    {
                        "application/pdf" => ".pdf",
                        "image/png" => ".png",
                        "image/jpeg" => ".jpg",
                        "image/jpg" => ".jpg",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" => ".xlsx",
                        "application/vnd.ms-excel" => ".xls",
                        "application/msword" => ".doc",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document" => ".docx",
                        _ => string.Empty
                    };

                    safeFileName += extension;
                }

                var tempFolder = Path.Combine(Path.GetTempPath(), "Mes.Wpf", "Drawings");
                Directory.CreateDirectory(tempFolder);

                var tempFilePath = Path.Combine(tempFolder, safeFileName);
                await File.WriteAllBytesAsync(tempFilePath, bytes);

                Process.Start(new ProcessStartInfo
                {
                    FileName = tempFilePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                _messageService.ShowError($"파일 열기 중 오류가 발생했습니다.\n{ex.Message}");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private void BrowseDrawingFile()
        {
            DrawingUploadPath = PickFile();
        }

        private void BrowseOriginalFile()
        {
            OriginalUploadPath = PickFile();
        }

        private void BrowsePlateFile()
        {
            PlateUploadPath = PickFile();
        }

        private void NewRevision()
        {
            SelectedRevision = null;
            RevisionEditModel.Clear();
            ClearUploadPaths();
            ClearDirtyFlags();

            RaiseFileStates();
        }

        private async Task ReloadSelectedRevisionAsync()
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
                return;

            var selectedRevisionId = RevisionEditModel.RevisionId.Value;

            await LoadRevisionListAsync(EditModel.DrawingId.Value);
            SelectedRevision = RevisionItems.FirstOrDefault(x => x.RevisionId == selectedRevisionId);

            RaiseFileStates();
        }

        private static MultipartFormDataContent BuildMultipartFileContent(string fileKind, string filePath, bool includeKind)
        {
            var content = new MultipartFormDataContent();

            if (includeKind)
                content.Add(new StringContent(fileKind), "file_kind");

            var stream = File.OpenRead(filePath);
            var fileContent = new StreamContent(stream);
            fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");

            content.Add(fileContent, "file", Path.GetFileName(filePath));
            return content;
        }

        private void LoadToEditModel(DrawingDto? item)
        {
            if (item == null)
            {
                EditModel.Clear();
                IsCodeEditable = true;
                return;
            }

            EditModel.LoadFromDto(item);
            IsCodeEditable = false;
        }

        private void LoadRevisionToEditModel(DrawingRevisionDto? item)
        {
            if (item == null)
            {
                RevisionEditModel.Clear();
                ClearUploadPaths();
                ClearDirtyFlags();
                RaiseFileStates();
                return;
            }

            RevisionEditModel.LoadFromDto(item);
            ClearUploadPaths();
            ClearDirtyFlags();
            RaiseFileStates();
        }

        private bool ValidateForSave()
        {
            if (string.IsNullOrWhiteSpace(EditModel.DrawingNo))
            {
                _messageService.ShowWarning("도면번호는 필수입니다.");
                return false;
            }

            return true;
        }

        private void NormalizeEditModel()
        {
            EditModel.DrawingNo = EditModel.DrawingNo?.Trim() ?? string.Empty;
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string> { "page=1", "size=100" };

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");

            if (SelectedUseYn == "사용")
                queryParts.Add("is_active=true");
            else if (SelectedUseYn == "미사용")
                queryParts.Add("is_active=false");

            return $"{ApiRoutes.Drawings}?{string.Join("&", queryParts)}";
        }

        private static string PickFile()
        {
            var dialog = new OpenFileDialog
            {
                Filter = "모든 파일|*.*"
            };

            return dialog.ShowDialog() == true ? dialog.FileName : string.Empty;
        }

        private void ClearUploadPaths()
        {
            _drawingUploadPath = string.Empty;
            _originalUploadPath = string.Empty;
            _plateUploadPath = string.Empty;

            OnPropertyChanged(nameof(DrawingUploadPath));
            OnPropertyChanged(nameof(OriginalUploadPath));
            OnPropertyChanged(nameof(PlateUploadPath));

            RaiseFileStates();
        }

        private void ClearUploadPath(string fileKind)
        {
            switch (fileKind)
            {
                case "DRAWING":
                    _drawingUploadPath = string.Empty;
                    OnPropertyChanged(nameof(DrawingUploadPath));
                    break;
                case "ORIGINAL":
                    _originalUploadPath = string.Empty;
                    OnPropertyChanged(nameof(OriginalUploadPath));
                    break;
                case "PLATE":
                    _plateUploadPath = string.Empty;
                    OnPropertyChanged(nameof(PlateUploadPath));
                    break;
            }

            RaiseFileStates();
        }

        private void ClearDirtyFlags()
        {
            IsDrawingFileDirty = false;
            IsOriginalFileDirty = false;
            IsPlateFileDirty = false;
            OnPropertyChanged(nameof(CanSaveChangedFiles));
        }

        private void ClearDirtyFlag(string fileKind)
        {
            switch (fileKind)
            {
                case "DRAWING":
                    IsDrawingFileDirty = false;
                    break;
                case "ORIGINAL":
                    IsOriginalFileDirty = false;
                    break;
                case "PLATE":
                    IsPlateFileDirty = false;
                    break;
            }

            OnPropertyChanged(nameof(CanSaveChangedFiles));
        }

        private bool HasRevisionFile(string fileKind)
        {
            return fileKind switch
            {
                "DRAWING" => RevisionEditModel.DrawingFileId.HasValue,
                "ORIGINAL" => RevisionEditModel.OriginalFileId.HasValue,
                "PLATE" => RevisionEditModel.PlateFileId.HasValue,
                _ => false
            };
        }

        private void RaiseFileStates()
        {
            OnPropertyChanged(nameof(DrawingUploadFileName));
            OnPropertyChanged(nameof(OriginalUploadFileName));
            OnPropertyChanged(nameof(PlateUploadFileName));

            OnPropertyChanged(nameof(DrawingDisplayFileName));
            OnPropertyChanged(nameof(OriginalDisplayFileName));
            OnPropertyChanged(nameof(PlateDisplayFileName));

            OnPropertyChanged(nameof(CanManageRevisionFiles));
            OnPropertyChanged(nameof(CanSaveChangedFiles));
        }

        private void RaiseAllStates()
        {
            RaiseFileStates();
            OnPropertyChanged(nameof(IsRevisionSectionEnabled));
            OnPropertyChanged(nameof(CanCreateRevision));
            OnPropertyChanged(nameof(CanManageRevisionFiles));
        }

        private static string GetFileKindDisplayName(string fileKind)
        {
            return fileKind switch
            {
                "DRAWING" => "도면파일",
                "ORIGINAL" => "원본파일",
                "PLATE" => "판작업파일",
                _ => "파일"
            };
        }
    }
}