using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace Mes.Vendor.Wpf.Infrastructure;

public sealed class ApiClient
{
    private const string NetworkErrorMessage =
        "서버에 연결할 수 없습니다. 네트워크와 서버 상태를 확인하세요.";
    private const string TimeoutErrorMessage =
        "요청 시간이 초과되었습니다. 잠시 후 다시 시도하세요.";

    private static readonly JsonSerializerOptions JsonOptions = CreateJsonOptions();
    private readonly HttpClient _httpClient;
    private readonly TimeSpan _normalTimeout;

    public ApiClient(ApiSettings settings)
    {
        ArgumentNullException.ThrowIfNull(settings);

        if (string.IsNullOrWhiteSpace(settings.BaseUrl))
        {
            throw new ArgumentException("API BaseUrl이 비어 있습니다.", nameof(settings));
        }

        if (settings.NormalTimeoutSeconds <= 0)
        {
            throw new ArgumentException("API 제한시간은 1초 이상이어야 합니다.", nameof(settings));
        }

        _normalTimeout = TimeSpan.FromSeconds(settings.NormalTimeoutSeconds);
        _httpClient = new HttpClient
        {
            BaseAddress = new Uri(settings.BaseUrl, UriKind.Absolute),
            Timeout = Timeout.InfiniteTimeSpan
        };
    }

    private static JsonSerializerOptions CreateJsonOptions()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web);
        options.Converters.Add(new KoreaDateTimeJsonConverter());
        return options;
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

    public Task<ApiResult<T>> GetAsync<T>(string relativeUrl)
    {
        return SendAndReadAsync<T>(
            cancellationToken => _httpClient.GetAsync(relativeUrl, cancellationToken),
            "GET 요청 실패");
    }

    public Task<ApiResult<TResponse>> PostAsync<TRequest, TResponse>(
        string relativeUrl,
        TRequest request)
    {
        return SendAndReadAsync<TResponse>(
            cancellationToken => _httpClient.PostAsJsonAsync(relativeUrl, request, cancellationToken),
            "POST 요청 실패");
    }

    private async Task<ApiResult<T>> SendAndReadAsync<T>(
        Func<CancellationToken, Task<HttpResponseMessage>> sendAsync,
        string errorPrefix)
    {
        using var timeoutCts = new CancellationTokenSource(_normalTimeout);

        try
        {
            using var response = await sendAsync(timeoutCts.Token);
            if (!response.IsSuccessStatusCode)
            {
                return ApiResult<T>.Fail(await BuildErrorMessageAsync(
                    response,
                    errorPrefix,
                    timeoutCts.Token));
            }

            var data = await response.Content.ReadFromJsonAsync<T>(
                JsonOptions,
                timeoutCts.Token);
            return ApiResult<T>.Ok(data);
        }
        catch (OperationCanceledException) when (timeoutCts.IsCancellationRequested)
        {
            return ApiResult<T>.Fail(TimeoutErrorMessage);
        }
        catch (HttpRequestException)
        {
            return ApiResult<T>.Fail(NetworkErrorMessage);
        }
        catch (Exception ex)
        {
            return ApiResult<T>.Fail($"요청 처리 중 오류가 발생했습니다: {ex.Message}");
        }
    }

    private static async Task<string> BuildErrorMessageAsync(
        HttpResponseMessage response,
        string defaultPrefix,
        CancellationToken cancellationToken)
    {
        try
        {
            var raw = await response.Content.ReadAsStringAsync(cancellationToken);
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
        catch (OperationCanceledException)
        {
            throw;
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
