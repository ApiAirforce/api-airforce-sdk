using System.Text.Json;

namespace Airforce;

/// <summary>Base exception for all SDK failures.</summary>
public class AirforceException : Exception
{
    public int Status { get; }
    public string? Code { get; }
    public string? Type { get; }
    public string? RequestId { get; }
    /// <summary>Seconds to wait before retrying, for 429 responses (0 if absent).</summary>
    public double RetryAfter { get; }
    public string? Body { get; }

    public AirforceException(
        string message,
        int status = 0,
        string? code = null,
        string? type = null,
        string? requestId = null,
        double retryAfter = 0,
        string? body = null,
        Exception? innerException = null)
        : base(message, innerException)
    {
        Status = status;
        Code = code;
        Type = type;
        RequestId = requestId;
        RetryAfter = retryAfter;
        Body = body;
    }

    public bool IsBadRequest => Status == 400;
    public bool IsAuthentication => Status == 401;
    public bool IsInsufficientBalance => Status == 402;
    public bool IsPermissionDenied => Status == 403;
    public bool IsNotFound => Status == 404;
    public bool IsConflict => Status == 409;
    public bool IsRateLimited => Status == 429;
    public bool IsServerError => Status >= 500;

    internal static AirforceException FromResponse(int status, string? body, string? requestId, double retryAfter)
    {
        string? message = null, code = null, type = null;
        if (!string.IsNullOrEmpty(body))
        {
            try
            {
                using var doc = JsonDocument.Parse(body);
                var root = doc.RootElement;
                if (root.TryGetProperty("error", out var err) && err.ValueKind == JsonValueKind.Object)
                {
                    message = GetString(err, "message");
                    code = GetString(err, "code");
                    type = GetString(err, "type");
                }
                else if (root.TryGetProperty("error", out var errStr) && errStr.ValueKind == JsonValueKind.String)
                {
                    message = errStr.GetString();
                }
                else
                {
                    message = GetString(root, "message");
                    code = GetString(root, "code");
                    type = GetString(root, "type");
                }
            }
            catch (JsonException)
            {
                // non-JSON body — fall through to a generic message
            }
        }
        message ??= $"Airforce API error (HTTP {status})";
        return new AirforceException(message, status, code, type, requestId, retryAfter, body);
    }

    private static string? GetString(JsonElement el, string name) =>
        el.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
}

/// <summary>A required credential (API key or session token) was not configured.</summary>
public sealed class MissingCredentialException : AirforceException
{
    public MissingCredentialException(string message) : base(message) { }
}

/// <summary>No HTTP response was received (DNS, TCP, TLS, transport failure).</summary>
public sealed class ApiConnectionException : AirforceException
{
    public ApiConnectionException(string message, Exception? inner = null) : base(message, innerException: inner) { }
}

/// <summary>The request exceeded the configured timeout.</summary>
public sealed class ApiTimeoutException : AirforceException
{
    public ApiTimeoutException(string message, Exception? inner = null) : base(message, innerException: inner) { }
}
