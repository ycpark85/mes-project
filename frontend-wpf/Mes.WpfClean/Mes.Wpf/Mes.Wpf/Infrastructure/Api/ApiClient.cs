using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Mes.Wpf.Core.Interfaces;
using Mes.Wpf.Core.Models;

namespace Mes.Wpf.Infrastructure.Api
{
    public class ApiClient : IApiClient
    {
        private readonly HttpClient _httpClient;

        public ApiClient(string baseUrl)
        {
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                throw new ArgumentException("API BaseUrl이 비어 있습니다.", nameof(baseUrl));
            }

            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(baseUrl)
            };
        }

        public async Task<ApiResult<T>> GetAsync<T>(string relativeUrl)
        {
            try
            {
                var response = await _httpClient.GetAsync(relativeUrl);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<T>
                    {
                        Success = false,
                        Message = $"GET 요청 실패: {(int)response.StatusCode}"
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<T>();

                return new ApiResult<T>
                {
                    Success = true,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<T>
                {
                    Success = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public async Task<ApiResult<TResponse>> PostAsync<TRequest, TResponse>(string relativeUrl, TRequest request)
        {
            try
            {
                var response = await _httpClient.PostAsJsonAsync(relativeUrl, request);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<TResponse>
                    {
                        Success = false,
                        Message = $"POST 요청 실패: {(int)response.StatusCode}"
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();

                return new ApiResult<TResponse>
                {
                    Success = true,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse>
                {
                    Success = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public async Task<ApiResult<TResponse>> PutAsync<TRequest, TResponse>(string relativeUrl, TRequest request)
        {
            try
            {
                var response = await _httpClient.PutAsJsonAsync(relativeUrl, request);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<TResponse>
                    {
                        Success = false,
                        Message = $"PUT 요청 실패: {(int)response.StatusCode}"
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();

                return new ApiResult<TResponse>
                {
                    Success = true,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse>
                {
                    Success = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public async Task<ApiResult<TResponse>> PatchAsync<TRequest, TResponse>(string relativeUrl, TRequest request)
        {
            try
            {
                using var requestMessage = new HttpRequestMessage(HttpMethod.Patch, relativeUrl)
                {
                    Content = JsonContent.Create(request)
                };

                var response = await _httpClient.SendAsync(requestMessage);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<TResponse>
                    {
                        Success = false,
                        Message = $"PATCH 요청 실패: {(int)response.StatusCode}"
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();

                return new ApiResult<TResponse>
                {
                    Success = true,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse>
                {
                    Success = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public async Task<ApiResult<bool>> DeleteAsync(string relativeUrl)
        {
            try
            {
                var response = await _httpClient.DeleteAsync(relativeUrl);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<bool>
                    {
                        Success = false,
                        Data = false,
                        Message = $"DELETE 요청 실패: {(int)response.StatusCode}"
                    };
                }

                return new ApiResult<bool>
                {
                    Success = true,
                    Data = true
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<bool>
                {
                    Success = false,
                    Data = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public async Task<ApiResult<T>> PostMultipartAsync<T>(string relativeUrl, MultipartFormDataContent content)
        {
            try
            {
                var response = await _httpClient.PostAsync(relativeUrl, content);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<T>
                    {
                        Success = false,
                        Message = $"POST Multipart 요청 실패: {(int)response.StatusCode}"
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<T>();

                return new ApiResult<T>
                {
                    Success = true,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<T>
                {
                    Success = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public async Task<ApiResult<T>> PatchMultipartAsync<T>(string relativeUrl, MultipartFormDataContent content)
        {
            try
            {
                using var requestMessage = new HttpRequestMessage(HttpMethod.Patch, relativeUrl)
                {
                    Content = content
                };

                var response = await _httpClient.SendAsync(requestMessage);

                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<T>
                    {
                        Success = false,
                        Message = $"PATCH Multipart 요청 실패: {(int)response.StatusCode}"
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<T>();

                return new ApiResult<T>
                {
                    Success = true,
                    Data = data
                };
            }
            catch (Exception ex)
            {
                return new ApiResult<T>
                {
                    Success = false,
                    Message = $"예외 발생: {ex.Message}"
                };
            }
        }

        public string BuildAbsoluteUrl(string relativeUrl)
        {
            return new Uri(_httpClient.BaseAddress!, relativeUrl).ToString();
        }
    }
}