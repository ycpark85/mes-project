using System.Threading.Tasks;
using Mes.Wpf.Core.Common;

namespace Mes.Wpf.Core.Common.ViewModels
{
    public abstract class CrudPageViewModelBase<TItem> : ViewModelBase
    {
        private bool _isLoading;
        private TItem? _selectedItem;

        protected CrudPageViewModelBase()
        {
            SearchCommand = new AsyncRelayCommand(SearchAsync);
            ResetCommand = new RelayCommand(Reset);
            NewCommand = new RelayCommand(New);
        }

        public AsyncRelayCommand SearchCommand { get; }
        public RelayCommand ResetCommand { get; }
        public RelayCommand NewCommand { get; }

        public bool IsLoading
        {
            get => _isLoading;
            set => SetProperty(ref _isLoading, value);
        }

        public TItem? SelectedItem
        {
            get => _selectedItem;
            set
            {
                if (SetProperty(ref _selectedItem, value))
                    OnSelectedItemChanged(value);
            }
        }

        protected async Task SearchAsync()
        {
            IsLoading = true;
            try
            {
                await LoadListAsync();
            }
            finally
            {
                IsLoading = false;
            }
        }

        protected abstract Task LoadListAsync();

        protected virtual void OnSelectedItemChanged(TItem? item) { }

        protected virtual void Reset() { }

        protected virtual void New() { }
    }
}