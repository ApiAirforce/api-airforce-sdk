import {
  DEFAULT_BASE_URL,
  Transport,
  type TransportConfig,
} from "./core/transport";
import { Chat } from "./resources/chat";
import { Messages } from "./resources/messages";
import { Responses } from "./resources/responses";
import { Gemini } from "./resources/gemini";
import { Models } from "./resources/models";
import { Images } from "./resources/images";
import { Audio } from "./resources/audio";
import { Video } from "./resources/video";
import { Voices } from "./resources/voices";
import { Account } from "./resources/account";
import { Keys } from "./resources/keys";
import { Billing } from "./resources/billing";
import { TwoFactor } from "./resources/twofa";
import { Auth } from "./resources/auth";
import { OAuth } from "./resources/oauth";

export interface ClientOptions {
  /**
   * Airforce API key (`sk-air-…`). Used for all `/v1/*` inference + media and
   * key-provisioning calls. Falls back to the `AIRFORCE_API_KEY` env var.
   */
  apiKey?: string;
  /**
   * Session JWT for account/billing endpoints (obtainable via auth.login()).
   * Falls back to the `AIRFORCE_SESSION_TOKEN` env var.
   */
  sessionToken?: string;
  /** Override the API base URL. Default: `https://api.airforce`. */
  baseURL?: string;
  /** Request timeout in milliseconds. Default: 60000. */
  timeout?: number;
  /** Max automatic retries on 429/5xx/network errors. Default: 2. */
  maxRetries?: number;
  /** Headers added to every request. */
  defaultHeaders?: Record<string, string>;
  /** Custom `fetch` implementation (for testing or non-standard runtimes). */
  fetch?: typeof fetch;
}

function readEnv(name: string): string | undefined {
  if (typeof process !== "undefined" && process.env) return process.env[name];
  return undefined;
}

/**
 * The Airforce API client.
 *
 * ```ts
 * const airforce = new Airforce({ apiKey: process.env.AIRFORCE_API_KEY });
 * const res = await airforce.chat.create({
 *   model: "claude-opus-4.8",
 *   messages: [{ role: "user", content: "Hello!" }],
 * });
 * ```
 */
export class Airforce {
  readonly baseURL: string;
  protected readonly transport: Transport;

  /** OpenAI-compatible chat completions (`/v1/chat/completions`). */
  readonly chat: Chat;
  /** Anthropic-compatible messages (`/v1/messages`). */
  readonly messages: Messages;
  /** OpenAI Responses API (`/v1/responses`). */
  readonly responses: Responses;
  /** Google Gemini-compatible generation (`/v1beta`). */
  readonly gemini: Gemini;
  /** Model catalog & discovery. */
  readonly models: Models;
  /** Image generation. */
  readonly images: Images;
  /** Audio: TTS, music, SFX, transcription, dubbing, voices. */
  readonly audio: Audio;
  /** Async video generation. */
  readonly video: Video;
  /** Voice cloning. */
  readonly voices: Voices;
  /** Account self-service (profile, prefs, sessions). */
  readonly account: Account;
  /** API key provisioning. */
  readonly keys: Keys;
  /** Billing, plans, public analytics. */
  readonly billing: Billing;
  /** Two-factor authentication. */
  readonly twofa: TwoFactor;
  /** Login / signup / session lifecycle. */
  readonly auth: Auth;
  /** OAuth 2.0 provider flow + app management. */
  readonly oauth: OAuth;

  constructor(options: ClientOptions = {}) {
    const apiKey = options.apiKey ?? readEnv("AIRFORCE_API_KEY");
    const sessionToken =
      options.sessionToken ?? readEnv("AIRFORCE_SESSION_TOKEN");
    const baseURL = options.baseURL ?? readEnv("AIRFORCE_BASE_URL") ?? DEFAULT_BASE_URL;

    if (!options.fetch && typeof fetch === "undefined") {
      throw new Error(
        "No global `fetch` found. Use Node >= 18, or pass a `fetch` implementation in ClientOptions.",
      );
    }

    const config: TransportConfig = {
      apiKey,
      sessionToken,
      baseURL,
      timeout: options.timeout ?? 60_000,
      maxRetries: options.maxRetries ?? 2,
      defaultHeaders: options.defaultHeaders ?? {},
      fetch: options.fetch ?? globalThis.fetch.bind(globalThis),
    };

    this.baseURL = baseURL;
    this.transport = new Transport(config);

    this.chat = new Chat(this.transport);
    this.messages = new Messages(this.transport);
    this.responses = new Responses(this.transport);
    this.gemini = new Gemini(this.transport);
    this.models = new Models(this.transport);
    this.images = new Images(this.transport);
    this.audio = new Audio(this.transport);
    this.video = new Video(this.transport);
    this.voices = new Voices(this.transport);
    this.account = new Account(this.transport);
    this.keys = new Keys(this.transport);
    this.billing = new Billing(this.transport);
    this.twofa = new TwoFactor(this.transport);
    this.auth = new Auth(this.transport);
    this.oauth = new OAuth(this.transport, baseURL);
  }

  /** Manually set the session token (e.g. a JWT obtained elsewhere). */
  setSessionToken(token: string | undefined): void {
    this.transport.setSessionToken(token);
  }
}
