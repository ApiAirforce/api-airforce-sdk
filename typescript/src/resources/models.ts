/**
 * Model catalog / discovery — `GET /v1/models`, `GET /api/models/:model/detail`,
 * `GET /api/models/:model/allowed-params`, `GET /v1/playground/model-classes`.
 */

import { APIResource, type RequestConfig } from "./resource";

export interface PriceTier {
  max_input_tokens: number | null;
  label: string;
  input_cents_per_1m: number;
  output_cents_per_1m: number | null;
  cache_read_cents_per_1m?: number | null;
  cache_write_5m_cents_per_1m?: number | null;
  cache_write_1h_cents_per_1m?: number | null;
}

/**
 * A public model entry. The catalog object is large and evolving; the commonly
 * used fields are typed and the rest are reachable via the index signature.
 */
export interface Model {
  id: string;
  object: "model";
  created: number;
  owned_by: string;
  supports_chat?: boolean;
  supports_images?: boolean;
  moderated?: boolean;
  moderated_categories?: string[];
  multiplier?: number | null;
  tier?: "free" | "paid";
  min_tier?: "free" | "sub_backup" | "sub" | "paid_only" | null;
  max_tokens?: number;
  status?: string;
  pricepermilliontokens?: number | null;
  output_pricepermilliontokens?: number | null;
  official_pricepermilliontokens?: number | null;
  price_tiers?: PriceTier[] | null;
  priceperthousandimages?: number | null;
  latency_ms?: number | null;
  ttft_ms?: number | null;
  supports_streaming?: boolean | null;
  supports_tools?: boolean | null;
  supports_vision?: boolean | null;
  supports_reasoning?: boolean | null;
  supports_documents?: boolean | null;
  supports_web_search?: boolean | null;
  supports_caching?: boolean | null;
  group?: string | null;
  media_type?: "image" | "video" | "audio" | "speech" | "voiceover" | "sfx" | null;
  context_length?: number | null;
  max_output_tokens?: number | null;
  input_modalities?: string[] | null;
  output_modalities?: string[] | null;
  knowledge_cutoff?: string | null;
  released_unix?: number | null;
  [key: string]: unknown;
}

export interface ModelList {
  object: "list";
  data: Model[];
}

export interface ListModelsParams {
  /** Include per-channel alias variants (`?channels=1`). */
  channels?: boolean;
}

export interface ModelClasses {
  cheapest: string[];
  smartest: string[];
  fastest: string[];
}

export class Models extends APIResource {
  /** List available models (auth optional; tier-gated when authenticated). */
  async list(
    params: ListModelsParams = {},
    options: RequestConfig = {},
  ): Promise<Model[]> {
    const res = await this.transport.request<ModelList>({
      method: "GET",
      path: "/v1/models",
      auth: "none",
      query: params.channels ? { channels: 1 } : undefined,
      ...options,
    });
    return res.data;
  }

  /** Fetch the per-model analytics + channel detail (public, brand-neutral). */
  detail(
    model: string,
    options: RequestConfig = {},
  ): Promise<Record<string, unknown>> {
    return this.transport.request({
      method: "GET",
      path: `/api/models/${encodeURIComponent(model)}/detail`,
      auth: "none",
      ...options,
    });
  }

  /** Fetch effective parameter bounds for a model (for UI validation). */
  allowedParams(
    model: string,
    options: RequestConfig = {},
  ): Promise<Record<string, unknown>> {
    return this.transport.request({
      method: "GET",
      path: `/api/models/${encodeURIComponent(model)}/allowed-params`,
      auth: "none",
      ...options,
    });
  }

  /** Playground filter buckets (cheapest / smartest / fastest). */
  classes(options: RequestConfig = {}): Promise<ModelClasses> {
    return this.transport.request({
      method: "GET",
      path: "/v1/playground/model-classes",
      auth: "none",
      ...options,
    });
  }
}
