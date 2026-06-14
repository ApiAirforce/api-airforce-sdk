using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json.Nodes;

namespace Airforce;

/// <summary>Parses a Server-Sent Events byte stream into a sequence of JSON events.</summary>
internal static class SseStream
{
    public static async IAsyncEnumerable<JsonNode> ParseAsync(
        Stream stream,
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        using var reader = new StreamReader(stream, Encoding.UTF8);
        var data = new StringBuilder();
        var hasData = false;

        string? line;
        while ((line = await reader.ReadLineAsync(ct).ConfigureAwait(false)) != null)
        {
            if (line.Length == 0)
            {
                if (!hasData) continue;
                var node = Emit(data, ref hasData, out var done);
                if (done) yield break;
                if (node != null) yield return node;
                continue;
            }
            if (line.StartsWith(':')) continue; // comment / keep-alive
            if (line.StartsWith("data:"))
            {
                var value = line.Substring(5);
                if (value.StartsWith(' ')) value = value.Substring(1);
                if (hasData) data.Append('\n');
                data.Append(value);
                hasData = true;
            }
        }

        if (hasData)
        {
            var node = Emit(data, ref hasData, out _);
            if (node != null) yield return node;
        }
    }

    private static JsonNode? Emit(StringBuilder data, ref bool hasData, out bool done)
    {
        var payload = data.ToString();
        data.Clear();
        hasData = false;
        if (payload == "[DONE]")
        {
            done = true;
            return null;
        }
        done = false;
        return JsonNode.Parse(payload);
    }
}
