namespace Mes.Wpf.Core.Interfaces
{
    public interface IMessageService
    {
        void ShowInfo(string message, string title = "알림");
        void ShowWarning(string message, string title = "경고");
        void ShowError(string message, string title = "오류");
        bool Confirm(string message, string title = "확인");
    }
}