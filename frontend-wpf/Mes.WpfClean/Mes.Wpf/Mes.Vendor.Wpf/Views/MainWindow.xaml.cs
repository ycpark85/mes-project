using System;
using System.Windows;
using Mes.Vendor.Wpf.ViewModels;

namespace Mes.Vendor.Wpf.Views;

public partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;
    private bool _initialized;

    public MainWindow(MainViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = viewModel;
        viewModel.RequestLogout += ViewModel_OnRequestLogout;
        Closed += (_, _) => viewModel.RequestLogout -= ViewModel_OnRequestLogout;
    }

    private async void MainWindow_OnLoaded(object sender, RoutedEventArgs e)
    {
        if (_initialized)
        {
            return;
        }

        _initialized = true;
        await _viewModel.InitializeAsync();
    }

    private void OpenNewWindowButton_OnClick(object sender, RoutedEventArgs e)
    {
        var window = new MainWindow(_viewModel)
        {
            Owner = this
        };

        window.Show();
    }

    private void ViewModel_OnRequestLogout(object? sender, EventArgs e)
    {
        Close();
    }
}
