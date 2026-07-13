using System;
using System.Collections.Generic;
using System.Linq;
using Mes.Wpf.Modules.OutsourceProcessingCosts.Dtos;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.ViewModels
{
    internal static class OutsourceProcessingCostSaveRequestBuilder
    {
        public static OutsourceProcessingCostSaveRequest Build(
            DateTime? settlementMonth,
            string processType,
            decimal? standardAmount,
            string standardMemo,
            decimal? actualAmount,
            DateTime? actualBillingMonth,
            string actualMemo,
            string remark)
        {
            return new OutsourceProcessingCostSaveRequest
            {
                SettlementMonth = NormalizeMonth(settlementMonth) ?? DateTime.Today,
                ProcessType = processType,
                StandardAmount = standardAmount,
                StandardMemo = EmptyToNull(standardMemo),
                ActualAmount = actualAmount,
                ActualBillingMonth = NormalizeMonth(actualBillingMonth),
                ActualMemo = EmptyToNull(actualMemo),
                Remark = EmptyToNull(remark)
            };
        }

        public static OutsourceProcessingCostSaveRequest BuildForTargets(
            DateTime? settlementMonth,
            string processType,
            decimal? standardAmount,
            string standardMemo,
            decimal? actualAmount,
            DateTime? actualBillingMonth,
            string actualMemo,
            string remark,
            IEnumerable<OutsourceProcessingCostTargetRowModel> targets)
        {
            var request = Build(
                settlementMonth,
                processType,
                standardAmount,
                standardMemo,
                actualAmount,
                actualBillingMonth,
                actualMemo,
                remark);
            var selectedTargets = targets.ToList();

            request.TargetWorkGroupIds = selectedTargets
                .Where(x => x.OutsourceWorkGroupId.HasValue)
                .Select(x => x.OutsourceWorkGroupId!.Value)
                .ToList();
            request.TargetLotIds = selectedTargets
                .Where(x => x.LotId.HasValue)
                .Select(x => x.LotId!.Value)
                .ToList();

            return request;
        }

        private static DateTime? NormalizeMonth(DateTime? value)
        {
            if (!value.HasValue)
            {
                return null;
            }

            return new DateTime(value.Value.Year, value.Value.Month, 1);
        }

        private static string? EmptyToNull(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
        }
    }
}
