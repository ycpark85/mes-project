using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;

namespace Mes.Vendor.Wpf.Infrastructure;

public sealed class ApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = CreateJsonOptions();
    private readonly HttpClient _httpClient;

    private static JsonSerializerOptions CreateJsonOptions()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);
        options.Converters.Add(new KoreaDateTimeJsonConverter());
        return options;
    }

    public ApiClient(string baseUrl)
    {
        _httpClient = new HttpClient
        {
            BaseAddress = new Uri(baseUrl, UriKind.Absolute),
            Timeout = TimeSpan.FromSeconds(30)
        };
    }

    public void SetAccessToken(string? accessToken)
    {
        _httpClient.DefaultRequestHeaders.Authorization = string.IsNullOrWhiteSpace(accessToken)
            ? null
            : new AuthenticationHeaderValue("Bearer", accessToken);
    }

    public void ClearAccessToken()
    {
        _httpClient.DefaultRequestHeaders.Authorization = null;
    }

    public async Task<ApiResult<T>> GetAsync<T>(string relativeUrl)
    {
        try
        {
            var response = await _httpClient.GetAsync(relativeUrl);
            if (!response.IsSuccessStatusCode)
            {
                return ApiResult<T>.Fail(await BuildErrorMessageAsync(response, "GET 요청 실패"));
            }

            return ApiResult<T>.Ok(await response.Content.ReadFromJsonAsync<T>(JsonOptions));
        }
        catch (Exception ex)
        {
            return ApiResult<T>.Fail($"예외 발생: {ex.Message}");
        }
    }

    public async Task<ApiResult<TResponse>> PostAsync<TRequest, TResponse>(
        string relativeUrl,
        TRequest request)
    {
        try
        {
            var response = await _httpClient.PostAsJsonAsync(relativeUrl, request);
            if (!response.IsSuccessStatusCode)
            {
                return ApiResult<TResponse>.Fail(await BuildErrorMessageAsync(response, "POST 요청 실패"));
            }

            return ApiResult<TResponse>.Ok(await response.Content.ReadFromJsonAsync<TResponse>(JsonOptions));
        }
        catch (Exception ex)
        {
            return ApiResult<TResponse>.Fail($"예외 발생: {ex.Message}");
        }
    }

    private static async Task<string> BuildErrorMessageAsync(HttpResponseMessage response, string defaultPrefix)
    {
        try
        {
            var raw = await response.Content.ReadAsStringAsync();
            if (!string.IsNullOrWhiteSpace(raw))
            {
                using var doc = JsonDocument.Parse(raw);
                if (doc.RootElement.ValueKind == JsonValueKind.Object
                    && doc.RootElement.TryGetProperty("detail", out var detail))
                {
                    var message = detail.GetString();
                    if (!string.IsNullOrWhiteSpace(message))
                    {
                        return message;
                    }
                }
            }
        }
        catch
        {
        }

        return $"{defaultPrefix}: {(int)response.StatusCode}";
    }
}

public sealed class ApiResult<T>
{
    public bool Success { get; private init; }
    public string? Message { get; private init; }
    public T? Data { get; private init; }

    public static ApiResult<T> Ok(T? data) => new() { Success = true, Data = data };
    public static ApiResult<T> Fail(string message) => new() { Success = false, Message = message };
}
