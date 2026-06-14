package com.airforce;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/** Minimal multipart/form-data body builder for file-upload endpoints. */
final class Multipart {

  static final class FilePart {
    final String field;
    final String filename;
    final byte[] data;

    FilePart(String field, String filename, byte[] data) {
      this.field = field;
      this.filename = filename;
      this.data = data;
    }
  }

  final byte[] body;
  final String contentType;

  private Multipart(byte[] body, String contentType) {
    this.body = body;
    this.contentType = contentType;
  }

  static Multipart build(Map<String, String> fields, List<FilePart> files) {
    String boundary = "airforceBoundary" + Long.toHexString(System.nanoTime());
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    try {
      for (Map.Entry<String, String> e : fields.entrySet()) {
        if (e.getValue() == null) {
          continue;
        }
        write(out, "--" + boundary + "\r\n");
        write(out, "Content-Disposition: form-data; name=\"" + e.getKey() + "\"\r\n\r\n");
        write(out, e.getValue());
        write(out, "\r\n");
      }
      for (FilePart f : files) {
        write(out, "--" + boundary + "\r\n");
        write(out, "Content-Disposition: form-data; name=\"" + f.field + "\"; filename=\"" + f.filename + "\"\r\n");
        write(out, "Content-Type: application/octet-stream\r\n\r\n");
        out.write(f.data);
        write(out, "\r\n");
      }
      write(out, "--" + boundary + "--\r\n");
    } catch (IOException e) {
      throw new AirforceException("airforce: failed building multipart body");
    }
    return new Multipart(out.toByteArray(), "multipart/form-data; boundary=" + boundary);
  }

  private static void write(ByteArrayOutputStream out, String s) throws IOException {
    out.write(s.getBytes(StandardCharsets.UTF_8));
  }
}
