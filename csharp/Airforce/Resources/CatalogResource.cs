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

    /// <summary>One model, the same entry <see cref="ListAsync"/> returns for it
    /// (<c>GET /v1/models/{model}</c>). Ids with slashes such as <c>BAAI/bge-reranker-v2-m3</c>
    /// keep their slashes; each segment is percent-encoded. An unknown id throws the API's 404
    /// error.</summary>
    public Task<JsonNode?> RetrieveAsync(string model, CancellationToken ct = default)
        => Transport.GetAsync("/v1/models/" + string.Join("/", model.Split('/').Select(Enc)), "none", null, ct);

    public Task<JsonNode?> DetailAsync(string model, CancellationToken ct = default)
        => Transport.GetAsync($"/api/models/{Enc(model)}/detail", "none", null, ct);

    public Task<JsonNode?> AllowedParamsAsync(string model, CancellationToken ct = default)
        => Transport.GetAsync($"/api/models/{Enc(model)}/allowed-params", "none", null, ct);

    public Task<JsonNode?> ClassesAsync(CancellationToken ct = default)
        => Transport.GetAsync("/v1/playground/model-classes", "none", null, ct);
}
