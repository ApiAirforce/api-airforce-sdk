using System.Text;

namespace Airforce;

internal static class Multipart
{
    public static (byte[] Body, string ContentType) Build(
        IDictionary<string, string> fields,
        IEnumerable<(string Field, string Filename, byte[] Data)> files)
    {
        var boundary = "airforceBoundary" + Guid.NewGuid().ToString("N");
        using var ms = new MemoryStream();

        void Write(string s)
        {
            var b = Encoding.UTF8.GetBytes(s);
            ms.Write(b, 0, b.Length);
        }

        foreach (var kv in fields)
        {
            if (kv.Value == null) continue;
            Write($"--{boundary}\r\n");
            Write($"Content-Disposition: form-data; name=\"{kv.Key}\"\r\n\r\n");
            Write(kv.Value);
            Write("\r\n");
        }
        foreach (var (field, filename, data) in files)
        {
            Write($"--{boundary}\r\n");
            Write($"Content-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\n");
            Write("Content-Type: application/octet-stream\r\n\r\n");
            ms.Write(data, 0, data.Length);
            Write("\r\n");
        }
        Write($"--{boundary}--\r\n");

        return (ms.ToArray(), $"multipart/form-data; boundary={boundary}");
    }
}
