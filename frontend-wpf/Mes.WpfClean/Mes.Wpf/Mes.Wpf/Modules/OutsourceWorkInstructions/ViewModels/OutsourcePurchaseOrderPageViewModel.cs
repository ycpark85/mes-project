using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels
{
    public class OutsourcePurchaseOrderPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private OutsourcePurchaseOrderTargetGroupRowModel? _selectedCutGroup;
        private OutsourcePurchaseOrderTargetGroupRowModel? _selectedPrintGroup;

        public OutsourcePurchaseOrderPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            CutGroups = new ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel>();
            PrintGroups = new ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel>();
            EditModel = new OutsourcePurchaseOrderEditModel();

            RefreshCommand = new AsyncRelayCommand(SearchAsync);
            ResetCommand = new RelayCommand(Reset);
            SaveCommand = new RelayCommand(Save);
            PrintCommand = new RelayCommand(Print);
        }

        public ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> CutGroups { get; }

        public ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> PrintGroups { get; }

        public OutsourcePurchaseOrderEditModel EditModel { get; }

        public AsyncRelayCommand RefreshCommand { get; }

        public RelayCommand ResetCommand { get; }

        public RelayCommand SaveCommand { get; }

        public RelayCommand PrintCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public OutsourcePurchaseOrderTargetGroupRowModel? SelectedCutGroup
        {
            get => _selectedCutGroup;
            set
            {
                if (SetProperty(ref _selectedCutGroup, value) && value != null)
                {
                    SelectedPrintGroup = null;
                    LoadEditModel(value);
                    OnPropertyChanged(nameof(SelectedGroup));
                }
            }
        }

        public OutsourcePurchaseOrderTargetGroupRowModel? SelectedPrintGroup
        {
            get => _selectedPrintGroup;
            set
            {
                if (SetProperty(ref _selectedPrintGroup, value) && value != null)
                {
                    SelectedCutGroup = null;
                    LoadEditModel(value);
                    OnPropertyChanged(nameof(SelectedGroup));
                }
            }
        }

        public OutsourcePurchaseOrderTargetGroupRowModel? SelectedGroup => SelectedCutGroup ?? SelectedPrintGroup;

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            IsLoading = true;

            try
            {
                await LoadGroupsAsync("CUT", CutGroups);
                await LoadGroupsAsync("PRINT", PrintGroups);
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task LoadGroupsAsync(
            string processType,
            ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> targetCollection)
        {
            var route = $"{ApiRoutes.OutsourcePurchaseOrderTargets}?process_type={Uri.EscapeDataString(processType)}";
            var result = await _apiClient.GetAsync<OutsourcePurchaseOrderTargetListDto>(route);

            if (!result.Success || result.Data == null)
            {
                targetCollection.Clear();
                _messageService.ShowError(result.Message ?? $"{processType} 발주 대상 조회 중 오류가 발생했습니다.");
                return;
            }

            var grouped = result.Data.Items
                .GroupBy(x => new
                {
                    x.OutsourceWorkInstructionId,
                    x.InstructionNo,
                    x.ProcessType
                })
                .Select(g =>
                {
                    var first = g.First();

                    var fileMap = new Dictionary<long, OutsourceWorkInstructionFileDto>();
                    foreach (var row in g)
                    {
                        foreach (var file in row.Files)
                        {
                            if (!fileMap.ContainsKey(file.OutsourceWorkInstructionFileId))
                            {
                                fileMap[file.OutsourceWorkInstructionFileId] = file;
                            }
                        }
                    }

                    return new OutsourcePurchaseOrderTargetGroupRowModel
                    {
                        OutsourceWorkInstructionId = first.OutsourceWorkInstructionId,
                        InstructionNo = first.InstructionNo,
                        InstructionDate = first.InstructionDate,
                        ProcessType = first.ProcessType,
                        IsBundle = first.IsBundle,
                        OutsourcePartnerId = first.OutsourcePartnerId,
                        OutsourcePartnerName = first.OutsourcePartnerName ?? string.Empty,
                        InboundPartnerName = first.InboundPartnerName,
                        Items = g.OrderBy(x => x.LotNo).ToList(),
                        Files = fileMap.Values.ToList()
                    };
                })
                .OrderByDescending(x => x.InstructionDate)
                .ThenByDescending(x => x.InstructionNo)
                .ToList();

            targetCollection.Clear();
            foreach (var item in grouped)
            {
                targetCollection.Add(item);
            }
        }

        private void LoadEditModel(OutsourcePurchaseOrderTargetGroupRowModel group)
        {
            EditModel.LoadFromGroup(group);
        }

        private void Reset()
        {
            SelectedCutGroup = null;
            SelectedPrintGroup = null;
            EditModel.Clear();
            _ = SearchAsync();
        }

        private void Save()
        {
            if (SelectedGroup == null)
            {
                _messageService.ShowWarning("발주서 작성 대상을 선택하세요.");
                return;
            }

            _messageService.ShowInfo(
                $"발주서 작성 데이터 입력 완료\n" +
                $"작업지시번호: {SelectedGroup.InstructionNo}\n" +
                $"공정: {SelectedGroup.ProcessType}\n" +
                $"합계금액: {EditModel.TotalAmount:N0}");
        }

        private void Print()
        {
            if (SelectedGroup == null)
            {
                _messageService.ShowWarning("출력할 발주 대상을 선택하세요.");
                return;
            }

            _messageService.ShowInfo(
                $"발주서 출력 준비\n" +
                $"작업지시번호: {SelectedGroup.InstructionNo}\n" +
                $"공정: {SelectedGroup.ProcessType}\n" +
                $"LOT: {SelectedGroup.LotSummary}");
        }
    }
}