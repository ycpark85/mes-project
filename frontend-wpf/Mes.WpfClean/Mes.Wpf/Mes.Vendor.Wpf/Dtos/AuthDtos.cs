using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mes.Vendor.Wpf.Dtos;

public sealed class AuthLoginRequest
{
    [JsonPropertyName("login_id")]
    public string LoginId { get; set; } = string.Empty;

    [JsonPropertyName("password")]
    public string Password { get; set; } = string.Empty;
}

public sealed class AuthLoginResponse
{
    [JsonPropertyName("access_token")]
    public string AccessToken { get; set; } = string.Empty;

    [JsonPropertyName("token_type")]
    public string TokenType { get; set; } = string.Empty;

    [JsonPropertyName("expires_in_minutes")]
    public int ExpiresInMinutes { get; set; }

    [JsonPropertyName("user")]
    public AuthUserDto? User { get; set; }

    [JsonPropertyName("roles")]
    public List<AuthRoleDto> Roles { get; set; } = new();

    [JsonPropertyName("permissions")]
    public List<string> Permissions { get; set; } = new();
}

public sealed class AuthUserDto
{
    [JsonPropertyName("user_id")]
    public long UserId { get; set; }

    [JsonPropertyName("login_id")]
    public string LoginId { get; set; } = string.Empty;

    [JsonPropertyName("user_name")]
    public string UserName { get; set; } = string.Empty;

    [JsonPropertyName("password_change_required")]
    public bool PasswordChangeRequired { get; set; }
}

public sealed class AuthRoleDto
{
    [JsonPropertyName("role_id")]
    public long RoleId { get; set; }

    [JsonPropertyName("role_code")]
    public string RoleCode { get; set; } = string.Empty;

    [JsonPropertyName("role_name")]
    public string RoleName { get; set; } = string.Empty;
}
