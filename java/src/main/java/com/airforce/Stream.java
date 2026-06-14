package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.Closeable;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;
import java.util.NoSuchElementException;

/**
 * A lazily-parsed, closeable iterator over Server-Sent Events. Each {@link JsonNode}
 * is one streaming event; iteration stops at the {@code [DONE]} sentinel.
 *
 * <pre>{@code
 * try (Stream stream = client.chat().createStream(params)) {
 *   for (JsonNode chunk : stream) {
 *     // ...
 *   }
 * }
 * }</pre>
 */
public class Stream implements Iterable<JsonNode>, Closeable {

  private final InputStream source;
  private final BufferedReader reader;
  private final ObjectMapper mapper;

  Stream(InputStream source, ObjectMapper mapper) {
    this.source = source;
    this.reader = new BufferedReader(new InputStreamReader(source, StandardCharsets.UTF_8));
    this.mapper = mapper;
  }

  @Override
  public Iterator<JsonNode> iterator() {
    return new Iterator<JsonNode>() {
      private JsonNode next;
      private boolean done;

      @Override
      public boolean hasNext() {
        if (done) {
          return false;
        }
        if (next == null) {
          next = readNext();
        }
        return next != null;
      }

      @Override
      public JsonNode next() {
        if (!hasNext()) {
          throw new NoSuchElementException();
        }
        JsonNode value = next;
        next = null;
        return value;
      }

      private JsonNode readNext() {
        try {
          StringBuilder data = new StringBuilder();
          boolean hasData = false;
          String line;
          while ((line = reader.readLine()) != null) {
            if (line.isEmpty()) {
              if (!hasData) {
                continue;
              }
              return emit(data.toString());
            }
            if (line.startsWith(":")) {
              continue; // comment / keep-alive
            }
            if (line.startsWith("data:")) {
              String value = line.substring(5);
              if (value.startsWith(" ")) {
                value = value.substring(1);
              }
              if (hasData) {
                data.append('\n');
              }
              data.append(value);
              hasData = true;
            }
          }
          if (hasData) {
            return emit(data.toString());
          }
          finish();
          return null;
        } catch (IOException e) {
          finish();
          throw new AirforceException.ApiConnection("airforce: stream read failed", e);
        }
      }

      private JsonNode emit(String payload) throws IOException {
        if (payload.equals("[DONE]")) {
          finish();
          return null;
        }
        return mapper.readTree(payload);
      }

      private void finish() {
        done = true;
        close();
      }
    };
  }

  @Override
  public void close() {
    try {
      reader.close();
    } catch (IOException ignored) {
      // best effort
    }
    try {
      source.close();
    } catch (IOException ignored) {
      // best effort
    }
  }
}
