using System.Text.Json;
using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Base class shared by all resource accessors.</summary>
public abstract class Resource
{
    private protected readonly Transport Transport;

    internal Resource(Transport transport) => Transport = transport;

    /// <summary>Percent-encode a dynamic path segment (e.g. a user-chosen alias).</summary>
    private protected static string Enc(string segment) => Uri.EscapeDataString(segment);

    /// <summary>Serialize an arbitrary request body to a mutable <see cref="JsonObject"/>.</summary>
    private protected static JsonObject ToObject(object body) =>
        body as JsonObject
        ?? JsonSerializer.SerializeToNode(body)?.AsObject()
        ?? new JsonObject();
}
