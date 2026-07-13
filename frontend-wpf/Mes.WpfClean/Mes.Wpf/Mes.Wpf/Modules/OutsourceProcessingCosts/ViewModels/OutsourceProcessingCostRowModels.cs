using System;
using System.Collections.Generic;
using System.Linq;
using Mes.Wpf.Core.Common;
using Mes.Wpf.Modules.OutsourceProcessingCosts.Dtos;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.ViewModels
{
    public record CodeNameOption(string Code, string Name);

    public class OutsourceProcessingCostTargetRowModel : BindableBase
    {
        private bool _isChecked;

        public bool IsChecked
        {
            get => _isChecked;
            set => SetProperty(ref _isChecked, value);
        }

        public string TargetKey { get; set; } = string.Empty;
        public string ProcessType { get; set; } = string.Empty;
        public string ProcessTypeName => OutsourceProcessingCostDisplayOptions.ProcessTypeName(ProcessType);
        public long? OutsourceWorkGroupId { get; set; }
        public long? LotId { get; set; }
        public string? InstructionNo { get; set; }
        public DateTime? InstructionDate { get; set; }
        public string? PartnerName { get; set; }
        public string? GroupSeq { get; set; }
        public bool IsBundle { get; set; }
        public int LotCount { get; set; }
        public string? RepresentativeLotNo { get; set; }
        public string LotNosText { get; set; } = string.Empty;
        public string ProductNamesText { get; set; } = string.Empty;
        public string ProductSpecText { get; set; } = string.Empty;
        public long? SheetQty { get; set; }
        public long? InstructionOutputQty { get; set; }
        public string AllocationBasisType { get; set; } = string.Empty;
        public decimal AllocationBasisValue { get; set; }
        public long? OutsourceProcessingCostGroupId { get; set; }
        public string? AlreadyCostGroupNo { get; set; }
        public string? CostStatusCode { get; set; }
        public string CostStatusName => string.IsNullOrWhiteSpace(CostStatusCode)
            ? OutsourceProcessingCostDisplayOptions.StatusName(OutsourceProcessingCostDisplayOptions.UnregisteredStatusCode)
            : IsCostVariance
                ? OutsourceProcessingCostDisplayOptions.StatusName(OutsourceProcessingCostDisplayOptions.CostVarianceStatusCode)
                : OutsourceProcessingCostDisplayOptions.StatusName(CostStatusCode);
        public string StatusVisualCode => IsCostVariance
            ? OutsourceProcessingCostDisplayOptions.CostVarianceStatusCode
            : string.IsNullOrWhiteSpace(CostStatusCode)
                ? OutsourceProcessingCostDisplayOptions.UnregisteredStatusCode
                : CostStatusCode;
        public decimal? StandardAmount { get; set; }
        public decimal? ActualAmount { get; set; }
        public decimal? AmountDifference { get; set; }
        public DateTime? SettlementMonth { get; set; }
        public List<OutsourceProcessingCostAllocationRowModel> Allocations { get; set; } = new();
        public bool IsActiveRegistered => CostStatusCode is OutsourceProcessingCostDisplayOptions.DraftStatusCode
            or OutsourceProcessingCostDisplayOptions.ClosedStatusCode;
        public bool IsCostVariance =>
            CostStatusCode == OutsourceProcessingCostDisplayOptions.DraftStatusCode
            && StandardAmount.HasValue
            && ActualAmount.HasValue
            && AmountDifference.HasValue
            && AmountDifference.Value != 0;

        public static OutsourceProcessingCostTargetRowModel FromDto(OutsourceProcessingCostTargetDto dto)
        {
            return new OutsourceProcessingCostTargetRowModel
            {
                TargetKey = dto.TargetKey,
                ProcessType = dto.ProcessType,
                OutsourceWorkGroupId = dto.OutsourceWorkGroupId,
                LotId = dto.LotId,
                InstructionNo = dto.InstructionNo,
                InstructionDate = dto.InstructionDate,
                PartnerName = dto.PartnerName,
                GroupSeq = dto.GroupSeq,
                IsBundle = dto.IsBundle,
                LotCount = dto.LotCount,
                RepresentativeLotNo = dto.RepresentativeLotNo,
                LotNosText = !string.IsNullOrWhiteSpace(dto.RepresentativeLotNo)
                    ? dto.RepresentativeLotNo
                    : string.Join(", ", dto.LotNos),
                ProductNamesText = !string.IsNullOrWhiteSpace(dto.RepresentativeProductName)
                    ? dto.RepresentativeProductName
                    : string.Join(", ", dto.ProductNames),
                ProductSpecText = string.Join(", ", dto.ProductSpecs),
                SheetQty = dto.SheetQty,
                InstructionOutputQty = dto.InstructionOutputQty,
                AllocationBasisType = OutsourceProcessingCostDisplayOptions.BasisTypeName(dto.AllocationBasisType),
                AllocationBasisValue = dto.AllocationBasisValue,
                OutsourceProcessingCostGroupId = dto.OutsourceProcessingCostGroupId,
                AlreadyCostGroupNo = dto.AlreadyCostGroupNo,
                CostStatusCode = dto.CostStatus,
                StandardAmount = dto.StandardAmount,
                ActualAmount = dto.ActualAmount,
                AmountDifference = dto.AmountDifference,
                SettlementMonth = dto.SettlementMonth,
                Allocations = dto.Allocations
                    .Select(OutsourceProcessingCostAllocationRowModel.FromDto)
                    .ToList()
            };
        }

    }

    public class OutsourceProcessingCostGroupRowModel
    {
        public long OutsourceProcessingCostGroupId { get; set; }
        public string CostGroupNo { get; set; } = string.Empty;
        public DateTime SettlementMonth { get; set; }
        public string ProcessType { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public bool CanEdit => Status == OutsourceProcessingCostDisplayOptions.DraftStatusCode;
        public decimal? StandardAmount { get; set; }
        public decimal? ActualAmount { get; set; }
        public decimal? AmountDifference { get; set; }
        public string? StandardMemo { get; set; }
        public DateTime? ActualBillingMonth { get; set; }
        public string? ActualMemo { get; set; }
        public string? Remark { get; set; }
        public List<OutsourceProcessingCostAllocationRowModel> Allocations { get; set; } = new();

        public static OutsourceProcessingCostGroupRowModel FromDto(OutsourceProcessingCostGroupDto dto)
        {
            return new OutsourceProcessingCostGroupRowModel
            {
                OutsourceProcessingCostGroupId = dto.OutsourceProcessingCostGroupId,
                CostGroupNo = dto.CostGroupNo,
                SettlementMonth = dto.SettlementMonth,
                ProcessType = dto.ProcessType,
                Status = dto.Status,
                StandardAmount = dto.StandardAmount,
                ActualAmount = dto.ActualAmount,
                AmountDifference = dto.AmountDifference,
                StandardMemo = dto.StandardMemo,
                ActualBillingMonth = dto.ActualBillingMonth,
                ActualMemo = dto.ActualMemo,
                Remark = dto.Remark,
                Allocations = dto.Allocations
                    .Select(OutsourceProcessingCostAllocationRowModel.FromDto)
                    .ToList()
            };
        }
    }

    public class OutsourceProcessingCostAllocationRowModel
    {
        public string LotNo { get; set; } = string.Empty;
        public string? ProductName { get; set; }
        public string ProductSpecText { get; set; } = string.Empty;
        public int? CutsPerSheet { get; set; }
        public long? SheetQty { get; set; }
        public long? InstructionOutputQty { get; set; }
        public string BasisTypeName { get; set; } = string.Empty;
        public decimal BasisValue { get; set; }
        public decimal? BasisAreaSqm { get; set; }
        public decimal AllocationRatioPercent { get; set; }
        public decimal? StandardAllocatedAmount { get; set; }
        public decimal? ActualAllocatedAmount { get; set; }
        public decimal? AmountDifference { get; set; }

        public static OutsourceProcessingCostAllocationRowModel FromDto(OutsourceProcessingCostAllocationDto dto)
        {
            return new OutsourceProcessingCostAllocationRowModel
            {
                LotNo = dto.LotNo,
                ProductName = dto.ProductName,
                ProductSpecText = BuildSpecText(dto),
                CutsPerSheet = dto.CutsPerSheet,
                SheetQty = dto.SheetQty,
                InstructionOutputQty = dto.InstructionOutputQty,
                BasisTypeName = OutsourceProcessingCostDisplayOptions.BasisTypeName(dto.BasisType),
                BasisValue = dto.BasisValue,
                BasisAreaSqm = dto.BasisAreaSqm,
                AllocationRatioPercent = dto.AllocationRatio * 100,
                StandardAllocatedAmount = dto.StandardAllocatedAmount,
                ActualAllocatedAmount = dto.ActualAllocatedAmount,
                AmountDifference = dto.AmountDifference
            };
        }

        private static string BuildSpecText(OutsourceProcessingCostAllocationDto dto)
        {
            if (dto.PanelWidthMm.HasValue && dto.PanelLengthMm.HasValue)
            {
                return $"{dto.PanelWidthMm}x{dto.PanelLengthMm}";
            }

            return dto.ProductSpec ?? string.Empty;
        }
    }
}
