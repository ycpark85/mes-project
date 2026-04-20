using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Threading.Tasks;
using static Mes.Wpf.Modules.OutsourceWorkInstructions.Dtos.OutsourcePurchaseOrderEditModel;

namespace Mes.Wpf.Modules.OutsourceWorkInstructions.ViewModels
{
    public class OutsourcePurchaseOrderPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private OutsourcePurchaseOrderBundleRowModel? _selectedBundle;

        public OutsourcePurchaseOrderPageViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            CutGroups = new ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel>();
            PrintGroups = new ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel>();
            Bundles = new ObservableCollection<OutsourcePurchaseOrderBundleRowModel>();
            CutEditModel = new OutsourceCutPurchaseOrderEditModel();

            RefreshCommand = new AsyncRelayCommand(SearchAsync);
            ResetCommand = new RelayCommand(Reset);
            SaveCommand = new RelayCommand(Save);
            PrintCommand = new RelayCommand(Print);
        }

        public ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> CutGroups { get; }

        public ObservableCollection<OutsourcePurchaseOrderTargetGroupRowModel> PrintGroups { get; }

        public ObservableCollection<OutsourcePurchaseOrderBundleRowModel> Bundles { get; }

        public OutsourceCutPurchaseOrderEditModel CutEditModel { get; }

        public AsyncRelayCommand RefreshCommand { get; }

        public RelayCommand ResetCommand { get; }

        public RelayCommand SaveCommand { get; }

        public RelayCommand PrintCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public OutsourcePurchaseOrderBundleRowModel? SelectedBundle
        {
            get => _selectedBundle;
            set
            {
                if (SetProperty(ref _selectedBundle, value))
                {
                    if (value != null && value.BundleType == "CUT")
                    {
                        CutEditModel.LoadFromBundle(value);
                    }
                    else
                    {
                        CutEditModel.Clear();
                    }

                    OnPropertyChanged(nameof(IsCutBundleSelected));
                }
            }
        }

        public bool IsCutBundleSelected => SelectedBundle?.BundleType == "CUT";

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
                BuildBundles();
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

        private void BuildBundles()
        {
            Bundles.Clear();

            if (CutGroups.Count > 0)
            {
                Bundles.Add(new OutsourcePurchaseOrderBundleRowModel
                {
                    BundleType = "CUT",
                    Title = "재단 발주묶음",
                    Groups = CutGroups.ToList(),
                    Items = CutGroups.SelectMany(x => x.Items).OrderBy(x => x.LotNo).ToList(),
                    Files = CutGroups.SelectMany(x => x.Files)
                        .GroupBy(x => x.OutsourceWorkInstructionFileId)
                        .Select(x => x.First())
                        .ToList()
                });
            }

            if (PrintGroups.Count > 0)
            {
                Bundles.Add(new OutsourcePurchaseOrderBundleRowModel
                {
                    BundleType = "PRINT",
                    Title = "인쇄 발주묶음",
                    Groups = PrintGroups.ToList(),
                    Items = PrintGroups.SelectMany(x => x.Items).OrderBy(x => x.LotNo).ToList(),
                    Files = PrintGroups.SelectMany(x => x.Files)
                        .GroupBy(x => x.OutsourceWorkInstructionFileId)
                        .Select(x => x.First())
                        .ToList()
                });
            }

            SelectedBundle = Bundles.FirstOrDefault();
            OnPropertyChanged(nameof(Bundles));
        }

        private void Reset()
        {
            SelectedBundle = null;
            CutEditModel.Clear();
            _ = SearchAsync();
        }

        private void Save()
        {
            if (SelectedBundle == null)
            {
                _messageService.ShowWarning("발주 대상을 선택하세요.");
                return;
            }

            _messageService.ShowInfo($"{SelectedBundle.Title} 저장 기능은 다음 단계에서 연결합니다.");
        }

        private void Print()
        {
            if (SelectedBundle == null)
            {
                _messageService.ShowWarning("출력할 발주 대상을 선택하세요.");
                return;
            }

            _messageService.ShowInfo($"{SelectedBundle.Title} 출력 기능은 다음 단계에서 연결합니다.");
        }
    }
}