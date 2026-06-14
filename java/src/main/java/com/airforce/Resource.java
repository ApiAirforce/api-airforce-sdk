package com.airforce;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/** Base class shared by all resource accessors. */
abstract class Resource {

  protected final Transport transport;

  Resource(Transport transport) {
    this.transport = transport;
  }

  /** Percent-encode a dynamic path segment (e.g. a user-chosen alias). */
  protected static String enc(String segment) {
    return URLEncoder.encode(segment, StandardCharsets.UTF_8).replace("+", "%20");
  }

  /** Copy params into a mutable map and overlay the given key/value. */
  protected static Map<String, Object> with(Map<String, Object> params, String key, Object value) {
    Map<String, Object> body = params == null ? new HashMap<>() : new HashMap<>(params);
    body.put(key, value);
    return body;
  }
}
