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

        private DrawingRevisionDto? _selectedRevision;

        private string _drawingUploadPath = string.Empty;
        private string _originalUploadPath = string.Empty;
        private string _plateUploadPath = string.Empty;

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

            CreateRevisionCommand = new AsyncRelayCommand(CreateRevisionAsync);
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

            OpenDrawingFileCommand = new RelayCommand(OpenDrawingFile);
            OpenOriginalFileCommand = new RelayCommand(OpenOriginalFile);
            OpenPlateFileCommand = new RelayCommand(OpenPlateFile);

            NewRevisionCommand = new RelayCommand(NewRevision);
        }

        public ObservableCollection<DrawingDto> Items { get; }
        public ObservableCollection<DrawingRevisionDto> RevisionItems { get; }
        public ObservableCollection<string> UseYnOptions { get; }

        public DrawingEditModel EditModel { get; }
        public DrawingRevisionEditModel RevisionEditModel { get; }

        public AsyncRelayCommand SaveCommand { get; }
        public AsyncRelayCommand DeleteCommand { get; }

        public AsyncRelayCommand CreateRevisionCommand { get; }
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
                    OnPropertyChanged(nameof(DrawingUploadFileName));
                    OnPropertyChanged(nameof(DrawingDisplayFileName));
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
                    OnPropertyChanged(nameof(OriginalUploadFileName));
                    OnPropertyChanged(nameof(OriginalDisplayFileName));
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
                    OnPropertyChanged(nameof(PlateUploadFileName));
                    OnPropertyChanged(nameof(PlateDisplayFileName));
                }
            }
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

            IsCodeEditable = true;
            LoadingMessage = "처리 중입니다...";

            OnPropertyChanged(nameof(DrawingDisplayFileName));
            OnPropertyChanged(nameof(OriginalDisplayFileName));
            OnPropertyChanged(nameof(PlateDisplayFileName));
            OnPropertyChanged(nameof(IsRevisionSectionEnabled));
            OnPropertyChanged(nameof(CanCreateRevision));
            OnPropertyChanged(nameof(CanManageRevisionFiles));
        }

        protected override void New()
        {
            SelectedItem = null;
            SelectedRevision = null;

            EditModel.Clear();
            RevisionEditModel.Clear();
            RevisionItems.Clear();
            ClearUploadPaths();

            IsCodeEditable = true;
            LoadingMessage = "처리 중입니다...";

            OnPropertyChanged(nameof(DrawingDisplayFileName));
            OnPropertyChanged(nameof(OriginalDisplayFileName));
            OnPropertyChanged(nameof(PlateDisplayFileName));
            OnPropertyChanged(nameof(IsRevisionSectionEnabled));
            OnPropertyChanged(nameof(CanCreateRevision));
            OnPropertyChanged(nameof(CanManageRevisionFiles));
        }

        protected override void OnSelectedItemChanged(DrawingDto? item)
        {
            LoadToEditModel(item);

            if (item == null)
            {
                RevisionItems.Clear();
                RevisionEditModel.Clear();
                ClearUploadPaths();

                OnPropertyChanged(nameof(DrawingDisplayFileName));
                OnPropertyChanged(nameof(OriginalDisplayFileName));
                OnPropertyChanged(nameof(PlateDisplayFileName));
                OnPropertyChanged(nameof(IsRevisionSectionEnabled));
                OnPropertyChanged(nameof(CanCreateRevision));
                OnPropertyChanged(nameof(CanManageRevisionFiles));
                return;
            }

            _ = LoadRevisionListAsync(item.DrawingId);

            OnPropertyChanged(nameof(IsRevisionSectionEnabled));
            OnPropertyChanged(nameof(CanCreateRevision));
            OnPropertyChanged(nameof(CanManageRevisionFiles));
        }

        private async Task SaveAsync()
        {
            NormalizeEditModel();

            if (!ValidateForSave())
                return;

            IsLoading = true;
            LoadingMessage = "도면 저장 중...";
            await Task.Yield();

            try
            {
                if (EditModel.DrawingId.HasValue)
                    await UpdateAsync(EditModel.DrawingId.Value);
                else
                    await CreateAsync();
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private async Task DeleteAsync()
        {
            if (SelectedItem == null || !EditModel.DrawingId.HasValue)
            {
                _messageService.ShowWarning("삭제할 항목을 먼저 선택하세요.");
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

                IsCodeEditable = true;

                OnPropertyChanged(nameof(DrawingDisplayFileName));
                OnPropertyChanged(nameof(OriginalDisplayFileName));
                OnPropertyChanged(nameof(PlateDisplayFileName));

                _messageService.ShowInfo("삭제되었습니다.");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private async Task CreateAsync()
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
                return;
            }

            await SearchAsync();

            SelectedItem = null;
            EditModel.Clear();
            IsCodeEditable = true;

            _messageService.ShowInfo("저장되었습니다.");
        }

        private async Task UpdateAsync(long drawingId)
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
                return;
            }

            await SearchAsync();

            SelectedItem = null;
            EditModel.Clear();
            IsCodeEditable = true;

            _messageService.ShowInfo("저장되었습니다.");
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

            var currentSelectedRevisionId = SelectedRevision?.RevisionId;

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

        private async Task CreateRevisionAsync()
        {
            if (!EditModel.DrawingId.HasValue)
            {
                _messageService.ShowWarning("먼저 도면을 저장하세요.");
                return;
            }

            RevisionEditModel.RevNo = RevisionEditModel.RevNo?.Trim() ?? string.Empty;

            if (string.IsNullOrWhiteSpace(RevisionEditModel.RevNo))
            {
                _messageService.ShowWarning("리비전 번호는 필수입니다.");
                return;
            }

            IsLoading = true;
            LoadingMessage = "리비전 생성 중...";
            await Task.Yield();

            try
            {
                var request = new DrawingRevisionCreateRequest
                {
                    RevNo = RevisionEditModel.RevNo,
                    SetAsCurrent = RevisionEditModel.SetAsCurrent
                };

                var result = await _apiClient.PostAsync<DrawingRevisionCreateRequest, DrawingRevisionDto>(
                    $"{ApiRoutes.Drawings}/{EditModel.DrawingId.Value}/revisions",
                    request);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "리비전 생성 중 오류가 발생했습니다.");
                    return;
                }

                await LoadRevisionListAsync(EditModel.DrawingId.Value);
                SelectedRevision = RevisionItems.FirstOrDefault(x => x.RevisionId == result.Data.RevisionId);

                _messageService.ShowInfo("리비전이 생성되었습니다.");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private async Task SetCurrentRevisionAsync()
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
            {
                _messageService.ShowWarning("현재 리비전으로 지정할 항목을 선택하세요.");
                return;
            }

            IsLoading = true;
            LoadingMessage = "현재 리비전 지정 중...";
            await Task.Yield();

            try
            {
                var result = await _apiClient.PostAsync<object, DrawingRevisionDto>(
                    $"{ApiRoutes.Drawings}/{EditModel.DrawingId.Value}/current-revision/{RevisionEditModel.RevisionId.Value}",
                    new { });

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "현재 리비전 지정 중 오류가 발생했습니다.");
                    return;
                }

                await SearchAsync();
                await LoadRevisionListAsync(EditModel.DrawingId.Value);

                _messageService.ShowInfo("현재 리비전으로 지정되었습니다.");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
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

            try
            {
                using var content = BuildMultipartFileContent(fileKind, filePath, true);

                var result = await _apiClient.PostMultipartAsync<DrawingRevisionFileDto>(
                    $"{ApiRoutes.Drawings}/{EditModel.DrawingId.Value}/revisions/{RevisionEditModel.RevisionId.Value}/files",
                    content);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? $"{GetFileKindDisplayName(fileKind)} 업로드 중 오류가 발생했습니다.");
                    return;
                }

                await ReloadSelectedRevisionAsync();
                ClearUploadPath(fileKind);

                _messageService.ShowInfo("파일이 업로드되었습니다.");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
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

            try
            {
                using var content = BuildMultipartFileContent(fileKind, filePath, false);

                var result = await _apiClient.PatchMultipartAsync<DrawingRevisionFileDto>(
                    $"{ApiRoutes.Drawings}/{EditModel.DrawingId.Value}/revisions/{RevisionEditModel.RevisionId.Value}/files/{fileKind}",
                    content);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? $"{GetFileKindDisplayName(fileKind)} 교체 중 오류가 발생했습니다.");
                    return;
                }

                await ReloadSelectedRevisionAsync();
                ClearUploadPath(fileKind);

                _messageService.ShowInfo("파일이 교체되었습니다.");
            }
            finally
            {
                IsLoading = false;
                LoadingMessage = "처리 중입니다...";
            }
        }

        private void OpenDrawingFile()
        {
            OpenRevisionFile(RevisionEditModel.DrawingFileId);
        }

        private void OpenOriginalFile()
        {
            OpenRevisionFile(RevisionEditModel.OriginalFileId);
        }

        private void OpenPlateFile()
        {
            OpenRevisionFile(RevisionEditModel.PlateFileId);
        }

        private void OpenRevisionFile(long? revisionFileId)
        {
            if (!revisionFileId.HasValue)
            {
                _messageService.ShowWarning("열 수 있는 파일이 없습니다.");
                return;
            }

            var url = _apiClient.BuildAbsoluteUrl($"{ApiRoutes.Drawings}/revision-files/{revisionFileId.Value}/download");

            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = url,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                _messageService.ShowError($"파일 열기 중 오류가 발생했습니다.\n{ex.Message}");
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

            OnPropertyChanged(nameof(DrawingDisplayFileName));
            OnPropertyChanged(nameof(OriginalDisplayFileName));
            OnPropertyChanged(nameof(PlateDisplayFileName));
            OnPropertyChanged(nameof(CanManageRevisionFiles));
        }

        private async Task ReloadSelectedRevisionAsync()
        {
            if (!EditModel.DrawingId.HasValue || !RevisionEditModel.RevisionId.HasValue)
                return;

            var selectedRevisionId = RevisionEditModel.RevisionId.Value;

            await LoadRevisionListAsync(EditModel.DrawingId.Value);
            SelectedRevision = RevisionItems.FirstOrDefault(x => x.RevisionId == selectedRevisionId);

            OnPropertyChanged(nameof(DrawingDisplayFileName));
            OnPropertyChanged(nameof(OriginalDisplayFileName));
            OnPropertyChanged(nameof(PlateDisplayFileName));
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

                OnPropertyChanged(nameof(DrawingDisplayFileName));
                OnPropertyChanged(nameof(OriginalDisplayFileName));
                OnPropertyChanged(nameof(PlateDisplayFileName));
                OnPropertyChanged(nameof(CanManageRevisionFiles));
                return;
            }

            RevisionEditModel.LoadFromDto(item);
            ClearUploadPaths();

            OnPropertyChanged(nameof(DrawingDisplayFileName));
            OnPropertyChanged(nameof(OriginalDisplayFileName));
            OnPropertyChanged(nameof(PlateDisplayFileName));
            OnPropertyChanged(nameof(CanManageRevisionFiles));
        }

        private bool ValidateForSave()
        {
            if (!EditModel.DrawingId.HasValue && string.IsNullOrWhiteSpace(EditModel.DrawingNo))
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
            DrawingUploadPath = string.Empty;
            OriginalUploadPath = string.Empty;
            PlateUploadPath = string.Empty;
        }

        private void ClearUploadPath(string fileKind)
        {
            switch (fileKind)
            {
                case "DRAWING":
                    DrawingUploadPath = string.Empty;
                    break;
                case "ORIGINAL":
                    OriginalUploadPath = string.Empty;
                    break;
                case "PLATE":
                    PlateUploadPath = string.Empty;
                    break;
            }
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