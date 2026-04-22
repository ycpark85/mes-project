using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
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

        private static async Task<string> BuildErrorMessageAsync(HttpResponseMessage response, string defaultPrefix)
        {
            try
            {
                var raw = await response.Content.ReadAsStringAsync();

                if (!string.IsNullOrWhiteSpace(raw))
                {
                    using var doc = JsonDocument.Parse(raw);

                    if (doc.RootElement.ValueKind == JsonValueKind.Object)
                    {
                        if (doc.RootElement.TryGetProperty("detail", out var detailElement))
                        {
                            var detail = detailElement.GetString();
                            if (!string.IsNullOrWhiteSpace(detail))
                            {
                                return detail;
                            }
                        }

                        if (doc.RootElement.TryGetProperty("message", out var messageElement))
                        {
                            var message = messageElement.GetString();
                            if (!string.IsNullOrWhiteSpace(message))
                            {
                                return message;
                            }
                        }
                    }
                }
            }
            catch
            {
            }

            return $"{defaultPrefix}: {(int)response.StatusCode}";
        }

        public async Task<ApiResult<TResponse>> GetAsync<TResponse>(string relativeUrl)
        {
            try
            {
                var response = await _httpClient.GetAsync(relativeUrl);
                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<TResponse>
                    {
                        Success = false,
                        Message = await BuildErrorMessageAsync(response, "GET 요청 실패")
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();
                return new ApiResult<TResponse> { Success = true, Data = data };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse> { Success = false, Message = $"예외 발생: {ex.Message}" };
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
                        Message = await BuildErrorMessageAsync(response, "POST 요청 실패")
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();
                return new ApiResult<TResponse> { Success = true, Data = data };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse> { Success = false, Message = $"예외 발생: {ex.Message}" };
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
                        Message = await BuildErrorMessageAsync(response, "PUT 요청 실패")
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();
                return new ApiResult<TResponse> { Success = true, Data = data };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse> { Success = false, Message = $"예외 발생: {ex.Message}" };
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
                        Message = await BuildErrorMessageAsync(response, "PATCH 요청 실패")
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();
                return new ApiResult<TResponse> { Success = true, Data = data };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse> { Success = false, Message = $"예외 발생: {ex.Message}" };
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
                        Message = await BuildErrorMessageAsync(response, "DELETE 요청 실패")
                    };
                }

                return new ApiResult<bool> { Success = true, Data = true };
            }
            catch (Exception ex)
            {
                return new ApiResult<bool> { Success = false, Data = false, Message = $"예외 발생: {ex.Message}" };
            }
        }

        public async Task<ApiResult<TResponse>> PostMultipartAsync<TResponse>(string relativeUrl, MultipartFormDataContent content)
        {
            try
            {
                var response = await _httpClient.PostAsync(relativeUrl, content);
                if (!response.IsSuccessStatusCode)
                {
                    return new ApiResult<TResponse>
                    {
                        Success = false,
                        Message = await BuildErrorMessageAsync(response, "POST Multipart 요청 실패")
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();
                return new ApiResult<TResponse> { Success = true, Data = data };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse> { Success = false, Message = $"예외 발생: {ex.Message}" };
            }
        }

        public async Task<ApiResult<TResponse>> PatchMultipartAsync<TResponse>(string relativeUrl, MultipartFormDataContent content)
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
                    return new ApiResult<TResponse>
                    {
                        Success = false,
                        Message = await BuildErrorMessageAsync(response, "PATCH Multipart 요청 실패")
                    };
                }

                var data = await response.Content.ReadFromJsonAsync<TResponse>();
                return new ApiResult<TResponse> { Success = true, Data = data };
            }
            catch (Exception ex)
            {
                return new ApiResult<TResponse> { Success = false, Message = $"예외 발생: {ex.Message}" };
            }
        }

        public string BuildAbsoluteUrl(string relativeUrl)
        {
            return new Uri(_httpClient.BaseAddress!, relativeUrl).ToString();
        }

        public async Task<byte[]?> GetBytesAsync(string uri)
        {
            try
            {
                using var response = await _httpClient.GetAsync(uri);
                if (!response.IsSuccessStatusCode)
                {
                    return null;
                }

                return await response.Content.ReadAsByteArrayAsync();
            }
            catch
            {
                return null;
            }
        }
    }
}