using System;
using System.Collections.Generic;
using Mes.Wpf.Core.Constants;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.ViewModels
{
    internal static class OutsourceProcessingCostQueryBuilder
    {
        public static string BuildCostGroupCollectionUrl()
        {
            return ApiRoutes.OutsourceProcessingCosts;
        }

        public static string BuildTargetUrl(
            string processType,
            DateTime? dateFrom,
            DateTime? dateTo,
            string selectedStatusCode,
            string searchKeyword)
        {
            var query = new List<string>
            {
                $"process_type={Uri.EscapeDataString(processType)}"
            };

            if (dateFrom.HasValue)
            {
                query.Add($"date_from={dateFrom.Value:yyyy-MM-dd}");
            }

            if (dateTo.HasValue)
            {
                query.Add($"date_to={dateTo.Value:yyyy-MM-dd}");
            }

            if (selectedStatusCode != OutsourceProcessingCostDisplayOptions.AllStatusCode)
            {
                query.Add($"status={Uri.EscapeDataString(selectedStatusCode)}");
            }

            if (!string.IsNullOrWhiteSpace(searchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(searchKeyword)}");
            }

            return $"{ApiRoutes.OutsourceProcessingCostTargets}?{string.Join("&", query)}";
        }

        public static string BuildCostGroupUrl(
            string processType,
            bool useSettlementMonth,
            DateTime? settlementMonth,
            string selectedStatusCode,
            string searchKeyword)
        {
            var query = new List<string>
            {
                $"process_type={Uri.EscapeDataString(processType)}"
            };

            if (useSettlementMonth && settlementMonth.HasValue)
            {
                query.Add($"settlement_month={settlementMonth.Value:yyyy-MM-dd}");
            }

            if (OutsourceProcessingCostDisplayOptions.IsCostGroupStatusFilter(selectedStatusCode))
            {
                query.Add($"status={Uri.EscapeDataString(selectedStatusCode)}");
            }

            if (!string.IsNullOrWhiteSpace(searchKeyword))
            {
                query.Add($"q={Uri.EscapeDataString(searchKeyword)}");
            }

            return $"{BuildCostGroupCollectionUrl()}?{string.Join("&", query)}";
        }

        public static string BuildCostGroupDetailUrl(long costGroupId)
        {
            return $"{BuildCostGroupCollectionUrl()}/{costGroupId}";
        }

        public static string BuildCostGroupStatusUrl(long costGroupId, string action)
        {
            return $"{BuildCostGroupDetailUrl(costGroupId)}/{action}";
        }
    }
}
