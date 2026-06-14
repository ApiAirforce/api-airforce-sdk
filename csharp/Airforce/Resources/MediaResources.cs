using System.Diagnostics;
using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Image generation — <c>POST /v1/images/generations</c>.</summary>
public sealed class ImagesResource : Resource
{
    internal ImagesResource(Transport t) : base(t) { }

    public Task<JsonNode?> GenerateAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/v1/images/generations", "api_key", request, ct);
}

/// <summary>Audio — TTS, music, SFX, transcription, dubbing, voices (<c>/v1/audio/*</c>).</summary>
public sealed class AudioResource : Resource
{
    internal AudioResource(Transport t) : base(t) { }

    public Task<byte[]> SpeechAsync(object request, CancellationToken ct = default)
        => Transport.PostBytesAsync("/v1/audio/speech", "api_key", request, ct);

    public Task<byte[]> MusicAsync(object request, CancellationToken ct = default)
        => Transport.PostBytesAsync("/v1/audio/music", "api_key", request, ct);

    public Task<byte[]> SoundEffectsAsync(object request, CancellationToken ct = default)
        => Transport.PostBytesAsync("/v1/audio/sound-effects", "api_key", request, ct);

    public Task<JsonNode?> TranscriptionsAsync(string model, byte[] file, string filename,
        IDictionary<string, string>? extra = null, CancellationToken ct = default)
        => MultipartJsonAsync("/v1/audio/transcriptions", Fields(model, extra), ("file", filename, file), ct);

    public Task<byte[]> AudioIsolationAsync(string model, byte[] file, string filename, string? output = null,
        CancellationToken ct = default)
    {
        var fields = new Dictionary<string, string> { ["model"] = model };
        if (output != null) fields["output"] = output;
        return MultipartBytesAsync("/v1/audio/audio-isolation", fields, ("file", filename, file), ct);
    }

    public Task<byte[]> VoiceChangerAsync(string model, byte[] file, string filename, string voice,
        CancellationToken ct = default)
        => MultipartBytesAsync("/v1/audio/voice-changer",
            new Dictionary<string, string> { ["model"] = model, ["voice"] = voice }, ("file", filename, file), ct);

    public Task<JsonNode?> DubbingAsync(string model, byte[] file, string filename, string targetLang,
        IDictionary<string, string>? extra = null, CancellationToken ct = default)
    {
        var fields = Fields(model, extra);
        fields["target_lang"] = targetLang;
        return MultipartJsonAsync("/v1/audio/dubbing", fields, ("file", filename, file), ct);
    }

    public Task<JsonNode?> DubbingStatusAsync(string id, CancellationToken ct = default)
        => Transport.GetAsync($"/v1/audio/dubbing/{Enc(id)}", "api_key", null, ct);

    public Task<byte[]> DubbingAudioAsync(string id, string lang, CancellationToken ct = default)
        => Transport.GetBytesAsync($"/v1/audio/dubbing/{Enc(id)}/audio/{Enc(lang)}", "api_key", ct);

    public async Task<JsonNode?> VoicesAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/v1/audio/voices", "api_key", null, ct).ConfigureAwait(false);
        return res?["voices"] ?? res;
    }

    private static Dictionary<string, string> Fields(string model, IDictionary<string, string>? extra)
    {
        var fields = new Dictionary<string, string> { ["model"] = model };
        if (extra != null)
            foreach (var kv in extra) fields[kv.Key] = kv.Value;
        return fields;
    }

    private Task<JsonNode?> MultipartJsonAsync(string path, IDictionary<string, string> fields,
        (string, string, byte[]) file, CancellationToken ct)
    {
        var (body, contentType) = Multipart.Build(fields, new[] { file });
        return Transport.RequestJsonAsync(HttpMethod.Post, path,
            new RequestOptions { Auth = "api_key", Body = body, ContentType = contentType }, ct);
    }

    private Task<byte[]> MultipartBytesAsync(string path, IDictionary<string, string> fields,
        (string, string, byte[]) file, CancellationToken ct)
    {
        var (body, contentType) = Multipart.Build(fields, new[] { file });
        return Transport.RequestBytesAsync(HttpMethod.Post, path,
            new RequestOptions { Auth = "api_key", Body = body, ContentType = contentType }, ct);
    }
}

/// <summary>Async video generation — <c>/v1/video/*</c>.</summary>
public sealed class VideoResource : Resource
{
    private static readonly HashSet<string> Terminal = new() { "completed", "failed", "expired" };

    internal VideoResource(Transport t) : base(t) { }

    public Task<JsonNode?> GenerateAsync(object request, CancellationToken ct = default)
        => Transport.PostAsync("/v1/video/generations", "api_key", request, ct);

    public Task<JsonNode?> GetTaskAsync(string id, CancellationToken ct = default)
        => Transport.GetAsync($"/v1/video/tasks/{Enc(id)}", "api_key", null, ct);

    public async Task<JsonNode?> ListTasksAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/v1/video/tasks", "api_key", null, ct).ConfigureAwait(false);
        return res?["data"] ?? res;
    }

    public Task<JsonNode?> DeleteTaskAsync(string id, CancellationToken ct = default)
        => Transport.DeleteAsync($"/v1/video/tasks/{Enc(id)}", "api_key", ct);

    /// <summary>Poll a task until it reaches a terminal state.</summary>
    public async Task<JsonNode?> WaitForCompletionAsync(string id, TimeSpan? pollInterval = null,
        TimeSpan? timeout = null, CancellationToken ct = default)
    {
        var interval = pollInterval ?? TimeSpan.FromMilliseconds(2500);
        var deadline = Stopwatch.GetTimestamp() + (long)((timeout ?? TimeSpan.FromMinutes(10)).TotalSeconds * Stopwatch.Frequency);
        while (true)
        {
            var task = await GetTaskAsync(id, ct).ConfigureAwait(false);
            var status = task?["status"]?.GetValue<string>() ?? "";
            if (status == "completed") return task;
            if (Terminal.Contains(status))
                throw new AirforceException($"airforce: video task {id} ended with status {status}", code: status);
            if (Stopwatch.GetTimestamp() > deadline)
                throw new AirforceException($"airforce: timed out waiting for video task {id}", code: "wait_timeout");
            await Task.Delay(interval, ct).ConfigureAwait(false);
        }
    }

    public async Task<JsonNode?> GenerateAndWaitAsync(object request, TimeSpan? pollInterval = null,
        TimeSpan? timeout = null, CancellationToken ct = default)
    {
        var task = await GenerateAsync(request, ct).ConfigureAwait(false);
        var id = task?["task_id"]?.GetValue<string>()
            ?? throw new AirforceException("airforce: video task response had no task_id");
        return await WaitForCompletionAsync(id, pollInterval, timeout, ct).ConfigureAwait(false);
    }
}

/// <summary>Voice cloning — <c>/v1/voices/*</c>.</summary>
public sealed class VoicesResource : Resource
{
    internal VoicesResource(Transport t) : base(t) { }

    public Task<JsonNode?> ConsentTextAsync(CancellationToken ct = default)
        => Transport.GetAsync("/v1/voices/consent-text", "none", null, ct);

    /// <summary>Create a cloned voice from one or more samples (filename + bytes).</summary>
    public Task<JsonNode?> CloneAsync(string name, string consentHash,
        IEnumerable<(string Filename, byte[] Data)> samples,
        IDictionary<string, string>? extra = null, CancellationToken ct = default)
    {
        var fields = new Dictionary<string, string> { ["name"] = name, ["consent_hash"] = consentHash };
        if (extra != null)
            foreach (var kv in extra) fields[kv.Key] = kv.Value;
        var files = samples.Select(s => ("files", s.Filename, s.Data));
        var (body, contentType) = Multipart.Build(fields, files);
        return Transport.RequestJsonAsync(HttpMethod.Post, "/v1/voices/clone",
            new RequestOptions { Auth = "api_key", Body = body, ContentType = contentType }, ct);
    }

    public async Task<JsonNode?> LibraryAsync(CancellationToken ct = default)
    {
        var res = await Transport.GetAsync("/v1/voices/library", "api_key", null, ct).ConfigureAwait(false);
        return res?["voices"] ?? res;
    }

    public Task<JsonNode?> UpdateAsync(string voiceId, object body, CancellationToken ct = default)
        => Transport.MethodAsync(HttpMethod.Patch, $"/v1/voices/clone/{Enc(voiceId)}", "api_key", body, ct);

    public Task<JsonNode?> DeleteAsync(string voiceId, CancellationToken ct = default)
        => Transport.DeleteAsync($"/v1/voices/clone/{Enc(voiceId)}", "api_key", ct);
}
