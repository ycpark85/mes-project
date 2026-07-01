using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Common.ViewModels;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OrderLines.Dtos;
using Mes.Wpf.Modules.RawMaterials.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.RawMaterials.ViewModels
{
    public class RawMaterialMasterPageViewModel : CrudPageViewModelBase<RawMaterialDto>
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;
        private RawMaterialLocationDto? _selectedLocation;
        private string _searchKeyword = string.Empty;
        private bool _isMaterialCodeEditable = true;
        private bool _isLocationCodeEditable = true;

        public RawMaterialMasterPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;
            Items = new ObservableCollection<RawMaterialDto>();
            Locations = new ObservableCollection<RawMaterialLocationDto>();
            LocationTypeOptions = new ObservableCollection<string> { "INTERNAL_WAREHOUSE", "OUTSOURCE_VENDOR", "OTHER" };
            MaterialEditModel = new RawMaterialEditModel();
            LocationEditModel = new RawMaterialLocationEditModel();
            SaveMaterialCommand = new AsyncRelayCommand(SaveMaterialAsync);
            DeleteMaterialCommand = new AsyncRelayCommand(DeleteMaterialAsync);
            NewMaterialCommand = new RelayCommand(NewMaterial);
            SaveLocationCommand = new AsyncRelayCommand(SaveLocationAsync);
            DeleteLocationCommand = new AsyncRelayCommand(DeleteLocationAsync);
            NewLocationCommand = new RelayCommand(NewLocation);
        }

        public ObservableCollection<RawMaterialDto> Items { get; }
        public ObservableCollection<RawMaterialLocationDto> Locations { get; }
        public ObservableCollection<string> LocationTypeOptions { get; }
        public RawMaterialEditModel MaterialEditModel { get; }
        public RawMaterialLocationEditModel LocationEditModel { get; }
        public IApiClient ApiClient => _apiClient;
        public IMessageService MessageService => _messageService;
        public AsyncRelayCommand SaveMaterialCommand { get; }
        public AsyncRelayCommand DeleteMaterialCommand { get; }
        public RelayCommand NewMaterialCommand { get; }
        public AsyncRelayCommand SaveLocationCommand { get; }
        public AsyncRelayCommand DeleteLocationCommand { get; }
        public RelayCommand NewLocationCommand { get; }

        public string SearchKeyword
        {
            get => _searchKeyword;
            set => SetProperty(ref _searchKeyword, value);
        }

        public bool IsMaterialCodeEditable
        {
            get => _isMaterialCodeEditable;
            set => SetProperty(ref _isMaterialCodeEditable, value);
        }

        public bool IsLocationCodeEditable
        {
            get => _isLocationCodeEditable;
            set => SetProperty(ref _isLocationCodeEditable, value);
        }

        public RawMaterialLocationDto? SelectedLocation
        {
            get => _selectedLocation;
            set
            {
                if (SetProperty(ref _selectedLocation, value))
                {
                    LoadLocationToEditModel(value);
                }
            }
        }

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        protected override async Task LoadListAsync()
        {
            await LoadMaterialsAsync();
            await LoadLocationsAsync();
        }

        protected override void Reset()
        {
            SearchKeyword = string.Empty;
            New();
            NewLocation();
        }

        protected override void New()
        {
            NewMaterial();
        }

        protected override void OnSelectedItemChanged(RawMaterialDto? item)
        {
            if (item == null)
            {
                NewMaterial();
                return;
            }
            MaterialEditModel.LoadFromDto(item);
            IsMaterialCodeEditable = false;
        }

        private async Task LoadMaterialsAsync()
        {
            var result = await _apiClient.GetAsync<RawMaterialListDto>(BuildMaterialListUrl());
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "원자재 품목 조회 중 오류가 발생했습니다.");
                return;
            }
            Items.Clear();
            foreach (var item in result.Data.Items)
            {
                Items.Add(item);
            }
        }

        private async Task LoadLocationsAsync()
        {
            var result = await _apiClient.GetAsync<RawMaterialLocationListDto>($"{ApiRoutes.RawMaterialLocations}?page=1&size=200&is_active=true");
            if (!result.Success || result.Data == null)
            {
                _messageService.ShowError(result.Message ?? "원자재 위치 조회 중 오류가 발생했습니다.");
                return;
            }
            Locations.Clear();
            foreach (var item in result.Data.Items)
            {
                Locations.Add(item);
            }
        }

        private void NewMaterial()
        {
            SelectedItem = null;
            MaterialEditModel.Clear();
            IsMaterialCodeEditable = true;
        }

        private void NewLocation()
        {
            SelectedLocation = null;
            LocationEditModel.Clear();
            IsLocationCodeEditable = true;
        }

        private async Task SaveMaterialAsync()
        {
            MaterialEditModel.MaterialCode = MaterialEditModel.MaterialCode.Trim();
            MaterialEditModel.MaterialName = MaterialEditModel.MaterialName.Trim();
            MaterialEditModel.Uom = string.IsNullOrWhiteSpace(MaterialEditModel.Uom) ? "M" : MaterialEditModel.Uom.Trim().ToUpperInvariant();
            if (string.IsNullOrWhiteSpace(MaterialEditModel.MaterialCode) && !MaterialEditModel.RawMaterialId.HasValue)
            {
                _messageService.ShowWarning("원자재코드는 필수입니다.");
                return;
            }
            if (string.IsNullOrWhiteSpace(MaterialEditModel.MaterialName))
            {
                _messageService.ShowWarning("원자재명은 필수입니다.");
                return;
            }

            if (MaterialEditModel.RawMaterialId.HasValue)
            {
                var request = new RawMaterialUpdateRequest
                {
                    MaterialName = MaterialEditModel.MaterialName,
                    MaterialSpec = MaterialEditModel.MaterialSpec,
                    WidthMm = MaterialEditModel.WidthMm,
                    MaterialType = MaterialEditModel.MaterialType,
                    Uom = MaterialEditModel.Uom,
                    StandardUnitCost = MaterialEditModel.StandardUnitCost,
                    IsActive = MaterialEditModel.IsActive,
                    Memo = MaterialEditModel.Memo
                };
                var result = await _apiClient.PatchAsync<RawMaterialUpdateRequest, RawMaterialDto>($"{ApiRoutes.RawMaterials}/{MaterialEditModel.RawMaterialId.Value}", request);
                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "원자재 품목 수정 중 오류가 발생했습니다.");
                    return;
                }
            }
            else
            {
                var request = new RawMaterialCreateRequest
                {
                    MaterialCode = MaterialEditModel.MaterialCode,
                    MaterialName = MaterialEditModel.MaterialName,
                    MaterialSpec = MaterialEditModel.MaterialSpec,
                    WidthMm = MaterialEditModel.WidthMm,
                    MaterialType = MaterialEditModel.MaterialType,
                    Uom = MaterialEditModel.Uom,
                    StandardUnitCost = MaterialEditModel.StandardUnitCost,
                    IsActive = MaterialEditModel.IsActive,
                    Memo = MaterialEditModel.Memo
                };
                var result = await _apiClient.PostAsync<RawMaterialCreateRequest, RawMaterialDto>(ApiRoutes.RawMaterials, request);
                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "원자재 품목 저장 중 오류가 발생했습니다.");
                    return;
                }
            }
            await SearchAsync();
            NewMaterial();
            _messageService.ShowInfo("저장되었습니다.");
        }

        private async Task DeleteMaterialAsync()
        {
            if (SelectedItem == null)
            {
                _messageService.ShowWarning("삭제할 원자재 품목을 선택하세요.");
                return;
            }
            if (!_messageService.Confirm($"[{SelectedItem.MaterialCode}] {SelectedItem.MaterialName} 품목을 미사용 처리하시겠습니까?", "삭제 확인"))
            {
                return;
            }
            var result = await _apiClient.DeleteAsync($"{ApiRoutes.RawMaterials}/{SelectedItem.RawMaterialId}");
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "원자재 품목 삭제 중 오류가 발생했습니다.");
                return;
            }
            await SearchAsync();
            NewMaterial();
        }

        private async Task SaveLocationAsync()
        {
            LocationEditModel.LocationCode = LocationEditModel.LocationCode.Trim();
            LocationEditModel.LocationName = LocationEditModel.LocationName.Trim();
            LocationEditModel.LocationType = LocationEditModel.LocationType.Trim().ToUpperInvariant();
            if (string.IsNullOrWhiteSpace(LocationEditModel.LocationName))
            {
                _messageService.ShowWarning("위치명은 필수입니다.");
                return;
            }

            if (LocationEditModel.RawMaterialLocationId.HasValue)
            {
                var request = new RawMaterialLocationUpdateRequest
                {
                    LocationName = LocationEditModel.LocationName,
                    LocationType = LocationEditModel.LocationType,
                    PartnerId = LocationEditModel.PartnerId,
                    IsActive = LocationEditModel.IsActive,
                    Memo = LocationEditModel.Memo
                };
                var result = await _apiClient.PatchAsync<RawMaterialLocationUpdateRequest, RawMaterialLocationDto>($"{ApiRoutes.RawMaterialLocations}/{LocationEditModel.RawMaterialLocationId.Value}", request);
                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "원자재 위치 수정 중 오류가 발생했습니다.");
                    return;
                }
            }
            else
            {
                var request = new RawMaterialLocationCreateRequest
                {
                    LocationCode = string.IsNullOrWhiteSpace(LocationEditModel.LocationCode)
                        ? null
                        : LocationEditModel.LocationCode,
                    LocationName = LocationEditModel.LocationName,
                    LocationType = LocationEditModel.LocationType,
                    PartnerId = LocationEditModel.PartnerId,
                    IsActive = LocationEditModel.IsActive,
                    Memo = LocationEditModel.Memo
                };
                var result = await _apiClient.PostAsync<RawMaterialLocationCreateRequest, RawMaterialLocationDto>(ApiRoutes.RawMaterialLocations, request);
                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "원자재 위치 저장 중 오류가 발생했습니다.");
                    return;
                }
            }
            await LoadLocationsAsync();
            NewLocation();
            _messageService.ShowInfo("저장되었습니다.");
        }

        public void ApplySelectedPartner(OrderLinePartnerLookupDto partner)
        {
            LocationEditModel.ApplyPartner(partner.PartnerId, partner.Name);
        }

        private async Task DeleteLocationAsync()
        {
            if (SelectedLocation == null)
            {
                _messageService.ShowWarning("삭제할 원자재 위치를 선택하세요.");
                return;
            }
            if (!_messageService.Confirm($"[{SelectedLocation.LocationCode}] {SelectedLocation.LocationName} 위치를 미사용 처리하시겠습니까?", "삭제 확인"))
            {
                return;
            }
            var result = await _apiClient.DeleteAsync($"{ApiRoutes.RawMaterialLocations}/{SelectedLocation.RawMaterialLocationId}");
            if (!result.Success)
            {
                _messageService.ShowError(result.Message ?? "원자재 위치 삭제 중 오류가 발생했습니다.");
                return;
            }
            await LoadLocationsAsync();
            NewLocation();
        }

        private void LoadLocationToEditModel(RawMaterialLocationDto? item)
        {
            if (item == null)
            {
                LocationEditModel.Clear();
                IsLocationCodeEditable = true;
                return;
            }
            LocationEditModel.LoadFromDto(item);
            IsLocationCodeEditable = false;
        }

        private string BuildMaterialListUrl()
        {
            var queryParts = new List<string> { "page=1", "size=200", "is_active=true" };
            if (!string.IsNullOrWhiteSpace(SearchKeyword))
            {
                queryParts.Add($"q={Uri.EscapeDataString(SearchKeyword.Trim())}");
            }
            return $"{ApiRoutes.RawMaterials}?{string.Join("&", queryParts)}";
        }
    }
}
