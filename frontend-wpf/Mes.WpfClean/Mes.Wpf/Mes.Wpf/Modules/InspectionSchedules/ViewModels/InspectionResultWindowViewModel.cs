using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Input;
using Microsoft.Win32;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;


namespace Mes.Wpf.Modules.InspectionSchedules.ViewModels
{
    public class InspectionResultWindowViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private long _inspectionScheduleId;
        private string _lotNo = string.Empty;
        private string _productName = string.Empty;
        private string _partnerName = string.Empty;
        private DateTime? _inspectionDate;
        private int _planQty;

        private DateTime? _dueDate;
        private int _orderQty;

        private int _accumulatedGoodQty;
        private int _accumulatedDefectQty;
        private int _accumulatedDefectShipQty;

        private int _goodQty;
        private int _defectShipQty;
        private int _defectQty;

        private bool _isPartial;
        private DateTime? _nextInspectionDate;
        private string _partialReason = string.Empty;

        private bool _isLoading;
        private InspectionResultDefectEditModel? _selectedDefect;

        public event Action<bool>? CloseRequested;

        public IApiClient ApiClient => _apiClient;
        public IMessageService MessageService => _messageService;

        public InspectionResultWindowViewModel(IApiClient apiClient, IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Defects = new ObservableCollection<InspectionResultDefectEditModel>();

            AddDefectCommand = new RelayCommand(_ => AddDefect());
            RemoveDefectCommand = new RelayCommand(x => RemoveDefect(x as InspectionResultDefectEditModel));
            UploadPhotoCommand = new RelayCommand(
                async x => await UploadPhotoAsync(x as InspectionResultDefectEditModel),
                x => !IsLoading && x is InspectionResultDefectEditModel);

            RemovePhotoCommand = new RelayCommand(x => RemovePhoto(x as DefectAttachmentEditModel));

            SaveCommand = new AsyncRelayCommand(SaveAsync, () => !IsLoading);
            CancelCommand = new RelayCommand(_ => CloseRequested?.Invoke(false));
        }

        public long InspectionScheduleId
        {
            get => _inspectionScheduleId;
            set => SetProperty(ref _inspectionScheduleId, value);
        }

        public string LotNo
        {
            get => _lotNo;
            set => SetProperty(ref _lotNo, value);
        }

        public string ProductName
        {
            get => _productName;
            set => SetProperty(ref _productName, value);
        }

        public string PartnerName
        {
            get => _partnerName;
            set => SetProperty(ref _partnerName, value);
        }

        public DateTime? DueDate
        {
            get => _dueDate;
            set => SetProperty(ref _dueDate, value);
        }

        public int OrderQty
        {
            get => _orderQty;
            set => SetProperty(ref _orderQty, value);
        }

        public DateTime? InspectionDate
        {
            get => _inspectionDate;
            set => SetProperty(ref _inspectionDate, value);
        }

        public int PlanQty
        {
            get => _planQty;
            set => SetProperty(ref _planQty, value);
        }

        public int AccumulatedGoodQty
        {
            get => _accumulatedGoodQty;
            set => SetProperty(ref _accumulatedGoodQty, value);
        }

        public int AccumulatedDefectQty
        {
            get => _accumulatedDefectQty;
            set => SetProperty(ref _accumulatedDefectQty, value);
        }

        public int AccumulatedDefectShipQty
        {
            get => _accumulatedDefectShipQty;
            set => SetProperty(ref _accumulatedDefectShipQty, value);
        }

        public int GoodQty
        {
            get => _goodQty;
            set
            {
                if (SetProperty(ref _goodQty, value))
                {
                    OnPropertyChanged(nameof(TotalQty));
                }
            }
        }

        public int DefectShipQty
        {
            get => _defectShipQty;
            set
            {
                if (SetProperty(ref _defectShipQty, value))
                {
                    OnPropertyChanged(nameof(TotalQty));
                }
            }
        }

        public int DefectQty
        {
            get => _defectQty;
            set
            {
                if (SetProperty(ref _defectQty, value))
                {
                    OnPropertyChanged(nameof(TotalQty));
                }
            }
        }

        public int TotalQty => GoodQty + DefectShipQty + DefectQty;

        public bool IsPartial
        {
            get => _isPartial;
            set => SetProperty(ref _isPartial, value);
        }

        public DateTime? NextInspectionDate
        {
            get => _nextInspectionDate;
            set => SetProperty(ref _nextInspectionDate, value);
        }

        public string PartialReason
        {
            get => _partialReason;
            set => SetProperty(ref _partialReason, value);
        }

        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (SetProperty(ref _isLoading, value))
                {
                    if (SaveCommand is AsyncRelayCommand saveCommand)
                    {
                        saveCommand.RaiseCanExecuteChanged();
                    }

                    if (UploadPhotoCommand is RelayCommand uploadPhotoCommand)
                    {
                        uploadPhotoCommand.RaiseCanExecuteChanged();
                    }
                }
            }
        }

        public ObservableCollection<InspectionResultDefectEditModel> Defects { get; }

        public InspectionResultDefectEditModel? SelectedDefect
        {
            get => _selectedDefect;
            set => SetProperty(ref _selectedDefect, value);
        }

        public ICommand AddDefectCommand { get; }
        public ICommand RemoveDefectCommand { get; }
        public ICommand UploadPhotoCommand { get; }
        public ICommand RemovePhotoCommand { get; }
        public ICommand SaveCommand { get; }
        public ICommand CancelCommand { get; }

        public async Task InitializeAsync(
            long inspectionScheduleId,
            string lotNo,
            string productName,
            string partnerName,
            DateTime? inspectionDate,
            int planQty,
            DateTime? dueDate,
            int orderQty)
        {
            InspectionScheduleId = inspectionScheduleId;
            LotNo = lotNo;
            ProductName = productName;
            PartnerName = partnerName;
            InspectionDate = inspectionDate;
            PlanQty = planQty;
            DueDate = dueDate;
            OrderQty = orderQty;

            await LoadAsync();
        }
        public void ApplySelectedDefectType(
            InspectionResultDefectEditModel defect,
            InspectionResultDefectTypeLookupDto selectedDefectType)     
        {
            if (defect == null || selectedDefectType == null)
            {
                return;
            }

            defect.DefectTypeId = (int)selectedDefectType.DefectTypeId;
            defect.DefectTypeName = selectedDefectType.DefectName?.Trim() ?? string.Empty;
            defect.DefectTypeMemo = selectedDefectType.Memo?.Trim() ?? string.Empty;
        }

        public void ClearSelectedDefectType(InspectionResultDefectEditModel defect)
        {
            if (defect == null)
            {
                return;
            }

            defect.DefectTypeId = null;
            defect.DefectTypeName = string.Empty;
            defect.DefectTypeMemo = string.Empty;
        }

        private async Task LoadAsync()
        {
            try
            {
                IsLoading = true;

                var result = await _apiClient.GetAsync<InspectionResultResponse>(
                    $"{ApiRoutes.InspectionSchedules}/{InspectionScheduleId}/result");

                if (!result.Success)
                {
                    return;
                }

                var dto = result.Data?.Result;
                if (dto == null)
                {
                    AccumulatedGoodQty = 0;
                    AccumulatedDefectQty = 0;
                    AccumulatedDefectShipQty = 0;
                    GoodQty = 0;
                    DefectShipQty = 0;
                    DefectQty = 0;
                    IsPartial = false;
                    NextInspectionDate = null;
                    PartialReason = string.Empty;
                    Defects.Clear();
                    return;
                }

                GoodQty = dto.GoodQty;
                DefectShipQty = dto.DefectShipQty;
                DefectQty = dto.DefectQty;

                IsPartial = dto.IsPartial;
                NextInspectionDate = dto.NextInspectionDate;
                PartialReason = dto.PartialReason ?? string.Empty;

                AccumulatedGoodQty = dto.GoodQty;
                AccumulatedDefectQty = dto.DefectQty;
                AccumulatedDefectShipQty = dto.DefectShipQty;

                Defects.Clear();

                if (dto.Defects != null)
                {
                    foreach (var defect in dto.Defects)
                    {
                        var edit = new InspectionResultDefectEditModel
                        {
                            DefectTypeId = defect.DefectTypeId,
                            DefectTypeName = string.Empty,
                            Memo = defect.Memo ?? string.Empty
                        };

                        if (defect.Attachments != null)
                        {
                            foreach (var att in defect.Attachments)
                            {
                                edit.Attachments.Add(new DefectAttachmentEditModel
                                {
                                    FileUri = att.FileUri,
                                    FileName = att.FileName ?? string.Empty,
                                    MimeType = att.MimeType ?? string.Empty,
                                    Memo = att.Memo ?? string.Empty
                                });
                            }
                        }

                        Defects.Add(edit);
                    }
                }
            }
            finally
            {
                IsLoading = false;
            }
        }

        private void AddDefect()
        {
            var item = new InspectionResultDefectEditModel();
            Defects.Add(item);
            SelectedDefect = item;
        }

        private void RemoveDefect(InspectionResultDefectEditModel? item)
        {
            if (item == null)
            {
                return;
            }

            Defects.Remove(item);
        }

        private void RemovePhoto(DefectAttachmentEditModel? item)
        {
            if (item == null)
            {
                return;
            }

            foreach (var defect in Defects)
            {
                if (defect.Attachments.Contains(item))
                {
                    defect.Attachments.Remove(item);
                    return;
                }
            }
        }

        private async Task UploadPhotoAsync(InspectionResultDefectEditModel? defect)
        {
            if (defect == null)
            {
                _messageService.ShowWarning("불량내역을 선택해주세요.");
                return;
            }

            var dialog = new OpenFileDialog
            {
                Filter = "Image Files|*.jpg;*.jpeg;*.png;*.bmp;*.webp",
                Multiselect = false
            };

            if (dialog.ShowDialog() != true)
            {
                return;
            }

            try
            {
                IsLoading = true;

                using var content = new MultipartFormDataContent();
                using var fileStream = File.OpenRead(dialog.FileName);
                using var streamContent = new StreamContent(fileStream);

                var ext = Path.GetExtension(dialog.FileName)?.ToLowerInvariant();
                streamContent.Headers.ContentType = ext switch
                {
                    ".jpg" or ".jpeg" => new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg"),
                    ".png" => new System.Net.Http.Headers.MediaTypeHeaderValue("image/png"),
                    ".bmp" => new System.Net.Http.Headers.MediaTypeHeaderValue("image/bmp"),
                    ".webp" => new System.Net.Http.Headers.MediaTypeHeaderValue("image/webp"),
                    _ => new System.Net.Http.Headers.MediaTypeHeaderValue("application/octet-stream")
                };

                content.Add(streamContent, "file", Path.GetFileName(dialog.FileName));

                var result = await _apiClient.PostMultipartAsync<DefectAttachmentUploadResponse>(
                    $"{ApiRoutes.InspectionSchedules}/{InspectionScheduleId}/result/photos",
                    content);

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "불량사진 업로드에 실패했습니다.");
                    return;
                }

                defect.Attachments.Add(new DefectAttachmentEditModel
                {
                    FileUri = result.Data.FileUri,
                    FileName = result.Data.FileName,
                    MimeType = result.Data.MimeType ?? string.Empty,
                    Memo = string.Empty
                });
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task SaveAsync()
        {
            if (TotalQty <= 0)
            {
                _messageService.ShowWarning("검수수량을 입력해주세요.");
                return;
            }

            if (IsPartial && !NextInspectionDate.HasValue)
            {
                _messageService.ShowWarning("분할검수일 경우 다음 검수일자를 입력해주세요.");
                return;
            }

            if (IsPartial && string.IsNullOrWhiteSpace(PartialReason))
            {
                _messageService.ShowWarning("분할검수일 경우 사유/메모를 입력해주세요.");
                return;
            }

            if (DefectQty > 0 && Defects.Count == 0)
            {
                _messageService.ShowWarning("불량수량이 있으면 불량내역을 등록해주세요.");
                return;
            }

            if (Defects.Any(x => !x.DefectTypeId.HasValue))
            {
                _messageService.ShowWarning("불량유형을 입력해주세요.");
                return;
            }

            try
            {
                IsLoading = true;

                var request = new InspectionResultUpsertRequest
                {
                    GoodQty = GoodQty,
                    DefectShipQty = DefectShipQty,
                    DefectQty = DefectQty,
                    IsPartial = IsPartial,
                    NextInspectionDate = IsPartial ? NextInspectionDate?.Date : null,
                    PartialReason = IsPartial ? PartialReason.Trim() : null
                };

                foreach (var defect in Defects)
                {
                    request.Defects.Add(new InspectionResultDefectRequest
                    {
                        DefectTypeId = defect.DefectTypeId ?? 0,
                        DefectQty = 0,
                        Disposition = "NOT_SHIPPABLE",
                        Memo = string.IsNullOrWhiteSpace(defect.Memo) ? null : defect.Memo.Trim(),
                        Attachments = new ObservableCollection<DefectAttachmentRequest>(
                            defect.Attachments.Select(x => new DefectAttachmentRequest
                            {
                                FileUri = x.FileUri,
                                FileName = string.IsNullOrWhiteSpace(x.FileName) ? null : x.FileName,
                                MimeType = string.IsNullOrWhiteSpace(x.MimeType) ? null : x.MimeType,
                                Memo = string.IsNullOrWhiteSpace(x.Memo) ? null : x.Memo.Trim()
                            }))
                    });
                }

                var result = await _apiClient.PutAsync<InspectionResultUpsertRequest, InspectionResultUpsertResponse>(
                    $"{ApiRoutes.InspectionSchedules}/{InspectionScheduleId}/result",
                    request);

                if (!result.Success)
                {
                    _messageService.ShowError(result.Message ?? "검수실적 저장에 실패했습니다.");
                    return;
                }

                _messageService.ShowInfo("검수실적이 저장되었습니다.");
                CloseRequested?.Invoke(true);
            }
            finally
            {
                IsLoading = false;
            }
        }
    }
}