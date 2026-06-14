package com.airforce;

import java.net.http.HttpClient;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * The api.airforce API client.
 *
 * <pre>{@code
 * Airforce client = Airforce.builder().apiKey("sk-air-...").build();
 * JsonNode res = client.chat().create(Map.of(
 *     "model", "claude-opus-4.8",
 *     "messages", List.of(Map.of("role", "user", "content", "hi"))));
 * }</pre>
 */
public final class Airforce {

  private final Transport transport;

  private final ChatResource chat;
  private final MessagesResource messages;
  private final ResponsesResource responses;
  private final GeminiResource gemini;
  private final ModelsResource models;
  private final ImagesResource images;
  private final AudioResource audio;
  private final VideoResource video;
  private final VoicesResource voices;
  private final AccountResource account;
  private final KeysResource keys;
  private final BillingResource billing;
  private final TwoFactorResource twofa;
  private final AuthResource auth;
  private final OAuthResource oauth;

  private Airforce(Builder b) {
    HttpClient http = b.httpClient != null
        ? b.httpClient
        : HttpClient.newBuilder().connectTimeout(b.timeout).build();

    String apiKey = b.apiKey != null ? b.apiKey : System.getenv("AIRFORCE_API_KEY");
    String sessionToken = b.sessionToken != null ? b.sessionToken : System.getenv("AIRFORCE_SESSION_TOKEN");
    String baseUrl = b.baseUrl;
    if (baseUrl == null) {
      String env = System.getenv("AIRFORCE_BASE_URL");
      baseUrl = env != null ? env : "https://api.airforce";
    }
    baseUrl = baseUrl.replaceAll("/+$", "");

    this.transport = new Transport(http, apiKey, sessionToken, baseUrl, b.timeout, b.maxRetries, b.headers);

    this.chat = new ChatResource(transport);
    this.messages = new MessagesResource(transport);
    this.responses = new ResponsesResource(transport);
    this.gemini = new GeminiResource(transport);
    this.models = new ModelsResource(transport);
    this.images = new ImagesResource(transport);
    this.audio = new AudioResource(transport);
    this.video = new VideoResource(transport);
    this.voices = new VoicesResource(transport);
    this.account = new AccountResource(transport);
    this.keys = new KeysResource(transport);
    this.billing = new BillingResource(transport);
    this.twofa = new TwoFactorResource(transport);
    this.auth = new AuthResource(transport);
    this.oauth = new OAuthResource(transport);
  }

  public static Builder builder() {
    return new Builder();
  }

  public ChatResource chat() {
    return chat;
  }

  public MessagesResource messages() {
    return messages;
  }

  public ResponsesResource responses() {
    return responses;
  }

  public GeminiResource gemini() {
    return gemini;
  }

  public ModelsResource models() {
    return models;
  }

  public ImagesResource images() {
    return images;
  }

  public AudioResource audio() {
    return audio;
  }

  public VideoResource video() {
    return video;
  }

  public VoicesResource voices() {
    return voices;
  }

  public AccountResource account() {
    return account;
  }

  public KeysResource keys() {
    return keys;
  }

  public BillingResource billing() {
    return billing;
  }

  public TwoFactorResource twofa() {
    return twofa;
  }

  public AuthResource auth() {
    return auth;
  }

  public OAuthResource oauth() {
    return oauth;
  }

  public void setSessionToken(String token) {
    transport.setSessionToken(token);
  }

  public String baseUrl() {
    return transport.baseUrl();
  }

  /** Fluent builder for {@link Airforce}. */
  public static final class Builder {
    private String apiKey;
    private String sessionToken;
    private String baseUrl;
    private Duration timeout = Duration.ofSeconds(60);
    private int maxRetries = 2;
    private final Map<String, String> headers = new HashMap<>();
    private HttpClient httpClient;

    public Builder apiKey(String apiKey) {
      this.apiKey = apiKey;
      return this;
    }

    public Builder sessionToken(String sessionToken) {
      this.sessionToken = sessionToken;
      return this;
    }

    public Builder baseUrl(String baseUrl) {
      this.baseUrl = baseUrl;
      return this;
    }

    public Builder timeout(Duration timeout) {
      this.timeout = timeout;
      return this;
    }

    public Builder maxRetries(int maxRetries) {
      this.maxRetries = maxRetries;
      return this;
    }

    public Builder header(String key, String value) {
      this.headers.put(key, value);
      return this;
    }

    public Builder httpClient(HttpClient httpClient) {
      this.httpClient = httpClient;
      return this;
    }

    public Airforce build() {
      return new Airforce(this);
    }
  }
}
