using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Common.ViewModels;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Core.Models;
using Mes.Wpf.Modules.DefectTypes.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.DefectTypes.ViewModels
{
    public class DefectTypePageViewModel : CrudPageViewModelBase<DefectTypeDto>
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private string _searchKeyword = string.Empty;
        private string _selectedUseYn = "사용";
        private bool _isLoading;
        private bool _isCodeEditable = true;
        private DefectTypeDto? _selectedItem;

        public DefectTypePageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<DefectTypeDto>();
            UseYnOptions = new ObservableCollection<string>
            {
                "사용",
                "미사용"
            };

            EditModel = new DefectTypeEditModel();

            
            SaveCommand = new AsyncRelayCommand(SaveAsync);
            DeleteCommand = new AsyncRelayCommand(DeleteAsync);
        }

        public ObservableCollection<DefectTypeDto> Items { get; }

        public ObservableCollection<string> UseYnOptions { get; }

        public DefectTypeEditModel EditModel { get; }

        //public AsyncRelayCommand SearchCommand { get; }

        //public RelayCommand ResetCommand { get; }

        //public RelayCommand NewCommand { get; }

        public AsyncRelayCommand SaveCommand { get; }

        public AsyncRelayCommand DeleteCommand { get; }

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

        //public bool IsLoading
        //{
        //    get => _isLoading;
        //    set => SetProperty(ref _isLoading, value);
        //}

        public bool IsCodeEditable
        {
            get => _isCodeEditable;
            set => SetProperty(ref _isCodeEditable, value);
        }

        //public DefectTypeDto? SelectedItem
        //{
        //    get => _selectedItem;
        //    set
        //    {
        //        if (SetProperty(ref _selectedItem, value))
        //        {
        //            LoadToEditModel(value);
        //        }
        //    }
        //}

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        //private async Task SearchAsync()
        //{
        //    IsLoading = true;

        //    try
        //    {
        //        var route = BuildListUrl();
        //        var result = await _apiClient.GetAsync<DefectTypeListDto>(route);

        //        if (!result.Success)
        //        {
        //            _messageService.ShowError(result.Message ?? "불량유형 조회 중 오류가 발생했습니다.");
        //            return;
        //        }

        //        Items.Clear();

        //        var source = result.Data?.Items ?? [];

        //        foreach (var item in source)
        //        {
        //            Items.Add(item);
        //        }

        //        if (SelectedItem != null && !Items.Any(x => x.DefectTypeId == SelectedItem.DefectTypeId))
        //        {
        //            SelectedItem = null;
        //        }
        //    }
        //    finally
        //    {
        //        IsLoading = false;
        //    }
        //}

        protected override async Task LoadListAsync()
        {
            var route = BuildListUrl();
            var result = await _apiClient.GetAsync<DefectTypeListDto>(route);

            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "불량유형 조회 오류");
                return;
            }

            Items.Clear();
            foreach (var item in result.Data?.Items ?? [])
                Items.Add(item);
        }

        protected override void OnSelectedItemChanged(DefectTypeDto? item)
        {
            LoadToEditModel(item);
        }

        protected override void Reset()
        {
            SearchKeyword = string.Empty;
            SelectedUseYn = "사용";
            SelectedItem = null;
            EditModel.Clear();
            IsCodeEditable = true;
        }

        protected override void New()
        {
            SelectedItem = null;
            EditModel.Clear();
            IsCodeEditable = true;
        }

        private async Task SaveAsync()
        {
            NormalizeEditModel();

            if (!ValidateForSave())
                return;

            IsLoading = true;

            try
            {
                if (EditModel.DefectTypeId.HasValue)
                {
                    await UpdateAsync(EditModel.DefectTypeId.Value);
                }
                else
                {
                    await CreateAsync();
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task DeleteAsync()
        {
            if (SelectedItem == null || !EditModel.DefectTypeId.HasValue)
            {
                _messageService.ShowWarning("삭제할 항목을 먼저 선택하세요.");
                return;
            }

            var confirm = System.Windows.MessageBox.Show(
                $"[{SelectedItem.DefectCode}] {SelectedItem.DefectName} 항목을 삭제하시겠습니까?",
                "삭제 확인",
                System.Windows.MessageBoxButton.YesNo,
                System.Windows.MessageBoxImage.Question);

            if (confirm != System.Windows.MessageBoxResult.Yes)
                return;

            IsLoading = true;

            try
            {
                var result = await _apiClient.DeleteAsync($"{ApiRoutes.DefectTypes}/{SelectedItem.DefectTypeId}");

                if (!result.Success || !result.Data)
                {
                    _messageService.ShowError(result.Message ?? "불량유형 삭제 중 오류가 발생했습니다.");
                    return;
                }

                await SearchAsync();
                SelectedItem = null;
                EditModel.Clear();
                IsCodeEditable = true;

                _messageService.ShowInfo("삭제되었습니다.");
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task CreateAsync()
        {
            var request = new DefectTypeCreateRequest
            {
                Code = EditModel.DefectCode,
                Name = EditModel.DefectName,
                Memo = EmptyToNull(EditModel.Memo),
                IsActive = EditModel.IsActive
            };

            var result = await _apiClient.PostAsync<DefectTypeCreateRequest, DefectTypeDto>(
                ApiRoutes.DefectTypes,
                request);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "불량유형 저장 중 오류가 발생했습니다.");
                return;
            }

            await SearchAsync();


            SelectedItem = null;
            EditModel.Clear();
            IsCodeEditable = true;

            _messageService.ShowInfo("저장되었습니다.");
        }

        private async Task UpdateAsync(long defectTypeId)
        {
            var request = new DefectTypeUpdateRequest
            {
                Name = EditModel.DefectName,
                Memo = EmptyToNull(EditModel.Memo),
                IsActive = EditModel.IsActive
            };

            var result = await _apiClient.PatchAsync<DefectTypeUpdateRequest, DefectTypeDto>(
                $"{ApiRoutes.DefectTypes}/{defectTypeId}",
                request);

            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "불량유형 수정 중 오류가 발생했습니다.");
                return;
            }

            await SearchAsync();
            SelectedItem = null;
            EditModel.Clear();
            IsCodeEditable = true;

            _messageService.ShowInfo("저장되었습니다.");
        }

        private void LoadToEditModel(DefectTypeDto? item)
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

        private bool ValidateForSave()
        {
            if (!EditModel.DefectTypeId.HasValue && string.IsNullOrWhiteSpace(EditModel.DefectCode))
            {
                _messageService.ShowWarning("불량코드는 필수입니다.");
                return false;
            }

            if (string.IsNullOrWhiteSpace(EditModel.DefectName))
            {
                _messageService.ShowWarning("불량명은 필수입니다.");
                return false;
            }

            return true;
        }

        private void NormalizeEditModel()
        {
            EditModel.DefectCode = EditModel.DefectCode?.Trim() ?? string.Empty;
            EditModel.DefectName = EditModel.DefectName?.Trim() ?? string.Empty;
            EditModel.Memo = EditModel.Memo?.Trim() ?? string.Empty;
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string>
            {
                "page=1",
                "size=100"
            };

            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }

            if (SelectedUseYn == "사용")
            {
                queryParts.Add("is_active=true");
            }
            else if (SelectedUseYn == "미사용")
            {
                queryParts.Add("is_active=false");
            }

            return $"{ApiRoutes.DefectTypes}?{string.Join("&", queryParts)}";
        }

        private static string? EmptyToNull(string? value)
        {
            return string.IsNullOrWhiteSpace(value) ? null : value;
        }
    }
}