using System.Windows;
using System.Windows.Controls;
using Mes.Wpf.Modules.InspectionSchedules.Dtos;
using Mes.Wpf.Modules.InspectionSchedules.ViewModels;

namespace Mes.Wpf.Modules.InspectionSchedules.Views
{
    public partial class InspectionScheduleManagementView : UserControl
    {
        public InspectionScheduleManagementView()
        {
            InitializeComponent();
        }

        private async void RowInspectionDatePicker_OnSelectedDateChanged(object sender, SelectionChangedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not DatePicker datePicker)
            {
                return;
            }

            if (datePicker.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            DateTime? previousDate = null;
            if (e.RemovedItems.Count > 0 && e.RemovedItems[0] is DateTime removedDate)
            {
                previousDate = removedDate.Date;
            }

            vm.SelectedItem = item;
            await vm.OnInspectionDatePickedAsync(previousDate, datePicker.SelectedDate);
        }

        private async void ReceiveButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.ReceiveAsync();
        }

        private async void InspectionActionButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button)
            {
                return;
            }

            if (button.Tag is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;

            if (item.Status == "RECEIVED")
            {
                await vm.StartAsync();
                return;
            }

            if (item.Status == "IN_PROGRESS")
            {
                await vm.OpenInspectionResultAsync();
            }
        }

        private async void CancelButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.CancelAsync();
        }

        private async void MoveUpButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.MoveUpAsync();
        }

        private async void MoveDownButton_OnClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is not InspectionScheduleManagementPageViewModel vm)
            {
                return;
            }

            if (sender is not Button button || button.DataContext is not InspectionScheduleListItemDto item)
            {
                return;
            }

            vm.SelectedItem = item;
            await vm.MoveDownAsync();
        }
    }
}