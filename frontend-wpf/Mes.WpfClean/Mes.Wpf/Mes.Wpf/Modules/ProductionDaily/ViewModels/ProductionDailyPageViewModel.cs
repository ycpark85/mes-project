using Mes.Wpf.Core.Common;
using Mes.Wpf.Core.Constants;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Modules.ProductionDaily.Dtos;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Threading.Tasks;
using System.Windows.Input;

namespace Mes.Wpf.Modules.ProductionDaily.ViewModels
{
    public class ProductionDailyPageViewModel : ViewModelBase
    {
        private readonly IApiClient _apiClient;
        private readonly IMessageService _messageService;

        private bool _isLoading;
        private string _partnerKeyword = string.Empty;
        private string _productKeyword = string.Empty;
        private string _selectedStatus = "IN_PROGRESS";
        private int _totalCount;

        public ProductionDailyPageViewModel(
            IApiClient apiClient,
            IMessageService messageService)
        {
            _apiClient = apiClient;
            _messageService = messageService;

            Items = new ObservableCollection<ProductionDailyRowDto>();
            StatusOptions = new ObservableCollection<ProductionDailyStatusOption>
            {
                new("IN_PROGRESS", "진행중"),
                new("COMPLETED", "완료")
            };

            SearchCommand = new AsyncRelayCommand(SearchAsync, () => !IsLoading);
            ResetCommand = new AsyncRelayCommand(ResetAsync, () => !IsLoading);
        }

        public ObservableCollection<ProductionDailyRowDto> Items { get; }
        public ObservableCollection<ProductionDailyStatusOption> StatusOptions { get; }
        public ICommand SearchCommand { get; }
        public ICommand ResetCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set
            {
                if (SetProperty(ref _isLoading, value))
                {
                    RaiseCommandCanExecuteChanged();
                }
            }
        }

        public string PartnerKeyword
        {
            get => _partnerKeyword;
            set => SetProperty(ref _partnerKeyword, value);
        }

        public string ProductKeyword
        {
            get => _productKeyword;
            set => SetProperty(ref _productKeyword, value);
        }

        public string SelectedStatus
        {
            get => _selectedStatus;
            set => SetProperty(ref _selectedStatus, value);
        }

        public int TotalCount
        {
            get => _totalCount;
            set => SetProperty(ref _totalCount, value);
        }

        public async Task InitializeAsync()
        {
            await SearchAsync();
        }

        private async Task SearchAsync()
        {
            IsLoading = true;

            try
            {
                var result = await _apiClient.GetAsync<ProductionDailyListDto>(BuildListUrl());

                if (!result.Success || result.Data == null)
                {
                    _messageService.ShowError(result.Message ?? "생산진행현황 조회 중 오류가 발생했습니다.");
                    return;
                }

                Items.Clear();

                foreach (var item in result.Data.Items)
                {
                    Items.Add(item);
                }

                TotalCount = result.Data.Total;
            }
            finally
            {
                IsLoading = false;
            }
        }

        private async Task ResetAsync()
        {
            PartnerKeyword = string.Empty;
            ProductKeyword = string.Empty;
            SelectedStatus = "IN_PROGRESS";

            await SearchAsync();
        }

        private string BuildListUrl()
        {
            var queryParts = new List<string>
            {
                "page=1",
                "size=200",
                $"status={Uri.EscapeDataString(SelectedStatus)}"
            };

            if (!string.IsNullOrWhiteSpace(PartnerKeyword))
            {
                queryParts.Add($"partner_q={Uri.EscapeDataString(PartnerKeyword.Trim())}");
            }

            if (!string.IsNullOrWhiteSpace(ProductKeyword))
            {
                queryParts.Add($"product_q={Uri.EscapeDataString(ProductKeyword.Trim())}");
            }

            return $"{ApiRoutes.ProductionDaily}?{string.Join("&", queryParts)}";
        }

        private void RaiseCommandCanExecuteChanged()
        {
            if (SearchCommand is AsyncRelayCommand searchCommand)
            {
                searchCommand.RaiseCanExecuteChanged();
            }

            if (ResetCommand is AsyncRelayCommand resetCommand)
            {
                resetCommand.RaiseCanExecuteChanged();
            }
        }
    }
}
