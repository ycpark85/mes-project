using System;
using System.Windows;
using Mes.Vendor.Wpf.Core;
using Mes.Vendor.Wpf.Dtos;

namespace Mes.Vendor.Wpf.Views;

public partial class WorkDoneWindow : Window
{
    private readonly WorkDoneDialogViewModel _viewModel;

    public WorkDoneWindow(BohyunOutsourceRow row)
    {
        InitializeComponent();
        _viewModel = new WorkDoneDialogViewModel(row);
        _viewModel.RequestClose += (_, accepted) =>
        {
            DialogResult = accepted;
            Close();
        };
        DataContext = _viewModel;
    }

    public int WorkDoneSheetQty => _viewModel.WorkDoneSheetQty;
    public decimal? OutsourceProcessingFee => _viewModel.OutsourceProcessingFee;
    public string? Remark => _viewModel.Remark;
}

public sealed class WorkDoneDialogViewModel : BindableBase
{
    private string _workDoneSheetQtyText;
    private string _outsourceProcessingFeeText = string.Empty;
    private string? _remark;
    private string _errorMessage = string.Empty;

    public WorkDoneDialogViewModel(BohyunOutsourceRow row)
    {
        Row = row;
        _workDoneSheetQtyText = row.SheetQty.ToString();
        SaveCommand = new RelayCommand(_ => Save());
        CancelCommand = new RelayCommand(_ => RequestClose?.Invoke(this, false));
    }

    public event EventHandler<bool>? RequestClose;

    public BohyunOutsourceRow Row { get; }
    public RelayCommand SaveCommand { get; }
    public RelayCommand CancelCommand { get; }

    public string InstructionNo => Row.InstructionNo;
    public string PartnerName => Row.PartnerName;
    public string WorkTypeName => Row.WorkTypeName;
    public string LotNosText => Row.LotNosText;
    public int SheetQty => Row.SheetQty;
    public string ProductNamesText => Row.ProductNamesText;
    public int WorkDoneSheetQty { get; private set; }
    public decimal? OutsourceProcessingFee { get; private set; }

    public string WorkDoneSheetQtyText
    {
        get => _workDoneSheetQtyText;
        set => SetProperty(ref _workDoneSheetQtyText, value);
    }

    public string? Remark
    {
        get => _remark;
        set => SetProperty(ref _remark, value);
    }

    public string OutsourceProcessingFeeText
    {
        get => _outsourceProcessingFeeText;
        set => SetProperty(ref _outsourceProcessingFeeText, value);
    }

    public string ErrorMessage
    {
        get => _errorMessage;
        private set => SetProperty(ref _errorMessage, value);
    }

    private void Save()
    {
        if (!int.TryParse(WorkDoneSheetQtyText, out var parsedQty) || parsedQty <= 0)
        {
            ErrorMessage = "완료 시트수를 입력해주세요.";
            return;
        }

        decimal? parsedFee = null;
        if (!string.IsNullOrWhiteSpace(OutsourceProcessingFeeText))
        {
            if (!decimal.TryParse(OutsourceProcessingFeeText, out var fee) || fee < 0)
            {
                ErrorMessage = "외주가공비는 0보다 작을 수 없습니다.";
                return;
            }

            parsedFee = fee;
        }

        WorkDoneSheetQty = parsedQty;
        OutsourceProcessingFee = parsedFee;
        RequestClose?.Invoke(this, true);
    }
}
