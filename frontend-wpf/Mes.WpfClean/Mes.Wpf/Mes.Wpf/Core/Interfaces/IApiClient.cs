using System.Net.Http;
using System.Threading.Tasks;
using Mes.Wpf.Core.Models;

namespace Mes.Wpf.Core.Interfaces
{
    public interface IApiClient
    {
        Task<ApiResult<T>> GetAsync<T>(string relativeUrl);
        Task<ApiResult<TResponse>> PostAsync<TRequest, TResponse>(string relativeUrl, TRequest request);
        Task<ApiResult<TResponse>> PostBulkAsync<TRequest, TResponse>(string relativeUrl, TRequest request);
        Task<ApiResult<TResponse>> PutAsync<TRequest, TResponse>(string relativeUrl, TRequest request);
        Task<ApiResult<TResponse>> PatchAsync<TRequest, TResponse>(string relativeUrl, TRequest request);
        Task<ApiResult<bool>> DeleteAsync(string relativeUrl);

        Task<ApiResult<T>> PostMultipartAsync<T>(string relativeUrl, MultipartFormDataContent content);
        Task<ApiResult<T>> PatchMultipartAsync<T>(string relativeUrl, MultipartFormDataContent content);

        Task<ApiResult<bool>> DownloadFileAsync(string relativeUrl, string destinationPath);

        string BuildAbsoluteUrl(string relativeUrl);

        void SetAccessToken(string? accessToken);
        void ClearAccessToken();
    }
}
