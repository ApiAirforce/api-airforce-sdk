using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Model catalog / discovery.</summary>
public sealed class ModelsResource : Resource
{
    internal ModelsResource(Transport t) : base(t) { }

    /// <summary>List public models. Returns the <c>data</c> array.</summary>
    public async Task<JsonNode?> ListAsync(bool channels = false, CancellationToken ct = default)
    {
        var query = channels ? new Dictionary<string, string?> { ["channels"] = "1" } : null;
        var res = await Transport.GetAsync("/v1/models", "none", query, ct).ConfigureAwait(false);
        return res?["data"] ?? res;
    }

    public Task<JsonNode?> DetailAsync(string model, CancellationToken ct = default)
        => Transport.GetAsync($"/api/models/{Enc(model)}/detail", "none", null, ct);

    public Task<JsonNode?> AllowedParamsAsync(string model, CancellationToken ct = default)
        => Transport.GetAsync($"/api/models/{Enc(model)}/allowed-params", "none", null, ct);

    public Task<JsonNode?> ClassesAsync(CancellationToken ct = default)
        => Transport.GetAsync("/v1/playground/model-classes", "none", null, ct);
}
