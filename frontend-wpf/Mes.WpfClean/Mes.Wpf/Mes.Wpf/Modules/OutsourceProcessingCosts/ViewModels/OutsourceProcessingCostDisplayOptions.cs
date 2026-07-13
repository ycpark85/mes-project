using System.Collections.Generic;

namespace Mes.Wpf.Modules.OutsourceProcessingCosts.ViewModels
{
    internal static class OutsourceProcessingCostDisplayOptions
    {
        public const string CutProcessTypeCode = "CUT";
        public const string PrintProcessTypeCode = "PRINT";
        public const string DieCutProcessTypeCode = "DIECUT";

        public const string AllStatusCode = "ALL";
        public const string UnregisteredStatusCode = "UNREGISTERED";
        public const string DraftStatusCode = "DRAFT";
        public const string CostVarianceStatusCode = "COST_VARIANCE";
        public const string ClosedStatusCode = "CLOSED";
        public const string CanceledStatusCode = "CANCELED";

        public const string AreaBasisTypeCode = "AREA";

        public static IReadOnlyList<CodeNameOption> ProcessTypes { get; } = new[]
        {
            new CodeNameOption(CutProcessTypeCode, "재단"),
            new CodeNameOption(PrintProcessTypeCode, "인쇄"),
            new CodeNameOption(DieCutProcessTypeCode, "도무송")
        };

        public static IReadOnlyList<CodeNameOption> Statuses { get; } = new[]
        {
            new CodeNameOption(AllStatusCode, "전체"),
            new CodeNameOption(UnregisteredStatusCode, "미등록"),
            new CodeNameOption(DraftStatusCode, "작성중"),
            new CodeNameOption(CostVarianceStatusCode, "원가차액"),
            new CodeNameOption(ClosedStatusCode, "월마감"),
            new CodeNameOption(CanceledStatusCode, "취소")
        };

        public static string ProcessTypeName(string processType)
        {
            return processType switch
            {
                CutProcessTypeCode => "재단",
                PrintProcessTypeCode => "인쇄",
                DieCutProcessTypeCode => "도무송",
                _ => processType
            };
        }

        public static string StatusName(string status)
        {
            return status switch
            {
                UnregisteredStatusCode => "미등록",
                DraftStatusCode => "작성중",
                CostVarianceStatusCode => "원가차액",
                ClosedStatusCode => "월마감",
                CanceledStatusCode => "취소",
                _ => status
            };
        }

        public static bool IsCostGroupStatusFilter(string statusCode)
        {
            return statusCode is DraftStatusCode
                or ClosedStatusCode
                or CanceledStatusCode
                or CostVarianceStatusCode;
        }

        public static string BasisTypeName(string basisType)
        {
            return basisType == AreaBasisTypeCode ? "면적" : "수량";
        }
    }
}
