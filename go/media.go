package airforce

import (
	"bytes"
	"context"
	"mime/multipart"
	"net/http"
	"net/url"
	"time"
)

type fileEntry struct {
	field    string
	filename string
	data     []byte
}

func buildMultipart(fields map[string]string, files []fileEntry) ([]byte, string, error) {
	var buf bytes.Buffer
	w := multipart.NewWriter(&buf)
	for k, v := range fields {
		if err := w.WriteField(k, v); err != nil {
			return nil, "", err
		}
	}
	for _, f := range files {
		fw, err := w.CreateFormFile(f.field, f.filename)
		if err != nil {
			return nil, "", err
		}
		if _, err := fw.Write(f.data); err != nil {
			return nil, "", err
		}
	}
	if err := w.Close(); err != nil {
		return nil, "", err
	}
	return buf.Bytes(), w.FormDataContentType(), nil
}

// --- images ------------------------------------------------------------------

// ImageInput is a reference image or a generated image (url or base64).
type ImageInput struct {
	URL     string `json:"url,omitempty"`
	B64JSON string `json:"b64_json,omitempty"`
}

// ImageParams is the request for Images.Generate.
type ImageParams struct {
	Model          string       `json:"model"`
	Prompt         string       `json:"prompt"`
	N              int          `json:"n,omitempty"`
	Size           string       `json:"size,omitempty"`
	Quality        string       `json:"quality,omitempty"`
	ResponseFormat string       `json:"response_format,omitempty"`
	AspectRatio    string       `json:"aspect_ratio,omitempty"`
	InputImages    []ImageInput `json:"input_images,omitempty"`
	Models         []string     `json:"models,omitempty"`
}

// ImagesResponse is the result of Images.Generate.
type ImagesResponse struct {
	Created int64        `json:"created,omitempty"`
	Data    []ImageInput `json:"data"`
}

// ImagesService accesses /v1/images.
type ImagesService struct{ client *Client }

// Generate creates one or more images from a prompt.
func (s *ImagesService) Generate(ctx context.Context, params ImageParams) (*ImagesResponse, error) {
	var out ImagesResponse
	err := s.client.postJSON(ctx, "/v1/images/generations", "api_key", params, &out)
	return &out, err
}

// --- audio -------------------------------------------------------------------

// SpeechParams is the request for Audio.Speech.
type SpeechParams struct {
	Model          string         `json:"model"`
	Input          string         `json:"input"`
	Voice          string         `json:"voice"`
	ResponseFormat string         `json:"response_format,omitempty"`
	Speed          *float64       `json:"speed,omitempty"`
	VoiceSettings  map[string]any `json:"voice_settings,omitempty"`
	LanguageCode   string         `json:"language_code,omitempty"`
	Seed           *int64         `json:"seed,omitempty"`
}

// MusicParams is the request for Audio.Music.
type MusicParams struct {
	Model           string         `json:"model"`
	Prompt          string         `json:"prompt"`
	MusicLengthMs   int            `json:"music_length_ms,omitempty"`
	ResponseFormat  string         `json:"response_format,omitempty"`
	CompositionPlan map[string]any `json:"composition_plan,omitempty"`
}

// SoundEffectParams is the request for Audio.SoundEffects.
type SoundEffectParams struct {
	Model           string   `json:"model"`
	Prompt          string   `json:"prompt"`
	DurationSeconds *float64 `json:"duration_seconds,omitempty"`
	PromptInfluence *float64 `json:"prompt_influence,omitempty"`
	ResponseFormat  string   `json:"response_format,omitempty"`
}

// DubbingJob is an async dubbing job.
type DubbingJob struct {
	DubbingID string `json:"dubbing_id"`
	Status    string `json:"status"`
	Error     string `json:"error,omitempty"`
}

// Voice is a TTS voice.
type Voice struct {
	VoiceID    string `json:"voice_id"`
	Name       string `json:"name"`
	PreviewURL string `json:"preview_url,omitempty"`
	Category   string `json:"category,omitempty"`
	Language   string `json:"language,omitempty"`
}

// AudioService accesses /v1/audio.
type AudioService struct{ client *Client }

func (s *AudioService) binary(ctx context.Context, path string, params any) ([]byte, error) {
	o, err := jsonOptions("api_key", params)
	if err != nil {
		return nil, err
	}
	return s.client.requestBytes(ctx, http.MethodPost, path, o)
}

// Speech converts text to speech and returns raw audio bytes.
func (s *AudioService) Speech(ctx context.Context, params SpeechParams) ([]byte, error) {
	return s.binary(ctx, "/v1/audio/speech", params)
}

// Music generates music and returns raw audio bytes.
func (s *AudioService) Music(ctx context.Context, params MusicParams) ([]byte, error) {
	return s.binary(ctx, "/v1/audio/music", params)
}

// SoundEffects generates a sound effect and returns raw audio bytes.
func (s *AudioService) SoundEffects(ctx context.Context, params SoundEffectParams) ([]byte, error) {
	return s.binary(ctx, "/v1/audio/sound-effects", params)
}

func (s *AudioService) multipartJSON(ctx context.Context, path string, fields map[string]string, file fileEntry, out any) error {
	body, ct, err := buildMultipart(fields, []fileEntry{file})
	if err != nil {
		return err
	}
	return s.client.requestJSON(ctx, http.MethodPost, path, requestOptions{auth: "api_key", body: body, contentType: ct}, out)
}

func (s *AudioService) multipartBinary(ctx context.Context, path string, fields map[string]string, file fileEntry) ([]byte, error) {
	body, ct, err := buildMultipart(fields, []fileEntry{file})
	if err != nil {
		return nil, err
	}
	return s.client.requestBytes(ctx, http.MethodPost, path, requestOptions{auth: "api_key", body: body, contentType: ct})
}

// Transcriptions transcribes an audio/video file. extra may carry language,
// prompt, temperature.
func (s *AudioService) Transcriptions(ctx context.Context, model string, file []byte, filename string, extra map[string]string) (map[string]any, error) {
	fields := map[string]string{"model": model}
	for k, v := range extra {
		fields[k] = v
	}
	var out map[string]any
	err := s.multipartJSON(ctx, "/v1/audio/transcriptions", fields, fileEntry{"file", filename, file}, &out)
	return out, err
}

// AudioIsolation isolates vocals/instrumental and returns raw audio bytes.
func (s *AudioService) AudioIsolation(ctx context.Context, model string, file []byte, filename, output string) ([]byte, error) {
	fields := map[string]string{"model": model}
	if output != "" {
		fields["output"] = output
	}
	return s.multipartBinary(ctx, "/v1/audio/audio-isolation", fields, fileEntry{"file", filename, file})
}

// VoiceChanger applies a target voice to an audio file and returns audio bytes.
func (s *AudioService) VoiceChanger(ctx context.Context, model string, file []byte, filename, voice string) ([]byte, error) {
	return s.multipartBinary(ctx, "/v1/audio/voice-changer", map[string]string{"model": model, "voice": voice}, fileEntry{"file", filename, file})
}

// Dubbing starts an async dubbing job. extra may carry source_lang, etc.
func (s *AudioService) Dubbing(ctx context.Context, model string, file []byte, filename, targetLang string, extra map[string]string) (*DubbingJob, error) {
	fields := map[string]string{"model": model, "target_lang": targetLang}
	for k, v := range extra {
		fields[k] = v
	}
	var out DubbingJob
	err := s.multipartJSON(ctx, "/v1/audio/dubbing", fields, fileEntry{"file", filename, file}, &out)
	return &out, err
}

// DubbingStatus polls a dubbing job.
func (s *AudioService) DubbingStatus(ctx context.Context, id string) (*DubbingJob, error) {
	var out DubbingJob
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/audio/dubbing/"+url.PathEscape(id), requestOptions{auth: "api_key"}, &out)
	return &out, err
}

// DubbingAudio fetches the dubbed audio for a completed job.
func (s *AudioService) DubbingAudio(ctx context.Context, id, lang string) ([]byte, error) {
	return s.client.requestBytes(ctx, http.MethodGet, "/v1/audio/dubbing/"+url.PathEscape(id)+"/audio/"+url.PathEscape(lang), requestOptions{auth: "api_key"})
}

// Voices lists available TTS voices.
func (s *AudioService) Voices(ctx context.Context) ([]Voice, error) {
	var out struct {
		Voices []Voice `json:"voices"`
	}
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/audio/voices", requestOptions{auth: "api_key"}, &out)
	return out.Voices, err
}

// --- video -------------------------------------------------------------------

// VideoParams is the request for Video.Generate.
type VideoParams struct {
	Model           string       `json:"model"`
	Prompt          string       `json:"prompt"`
	Mode            string       `json:"mode,omitempty"`
	DurationSeconds int          `json:"duration_seconds,omitempty"`
	AspectRatio     string       `json:"aspect_ratio,omitempty"`
	Quality         string       `json:"quality,omitempty"`
	InputImages     []ImageInput `json:"input_images,omitempty"`
}

// VideoTask is an async video generation task.
type VideoTask struct {
	TaskID    string `json:"task_id"`
	Status    string `json:"status"`
	Model     string `json:"model"`
	Created   int64  `json:"created"`
	Progress  int    `json:"progress,omitempty"`
	ResultURL string `json:"result_url,omitempty"`
	Error     string `json:"error,omitempty"`
	CostCents *int   `json:"cost_cents,omitempty"`
	ExpiresAt int64  `json:"expires_at,omitempty"`
}

// VideoService accesses /v1/video.
type VideoService struct{ client *Client }

// Generate creates an async video task.
func (s *VideoService) Generate(ctx context.Context, params VideoParams) (*VideoTask, error) {
	var out VideoTask
	err := s.client.postJSON(ctx, "/v1/video/generations", "api_key", params, &out)
	return &out, err
}

// GetTask returns the current state of a task.
func (s *VideoService) GetTask(ctx context.Context, id string) (*VideoTask, error) {
	var out VideoTask
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/video/tasks/"+url.PathEscape(id), requestOptions{auth: "api_key"}, &out)
	return &out, err
}

// ListTasks returns the caller's recent tasks.
func (s *VideoService) ListTasks(ctx context.Context) ([]VideoTask, error) {
	var out struct {
		Data []VideoTask `json:"data"`
	}
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/video/tasks", requestOptions{auth: "api_key"}, &out)
	return out.Data, err
}

// DeleteTask removes a task from history.
func (s *VideoService) DeleteTask(ctx context.Context, id string) error {
	return s.client.requestJSON(ctx, http.MethodDelete, "/v1/video/tasks/"+url.PathEscape(id), requestOptions{auth: "api_key"}, nil)
}

// WaitForCompletion polls a task until it reaches a terminal state.
func (s *VideoService) WaitForCompletion(ctx context.Context, id string, pollInterval, timeout time.Duration) (*VideoTask, error) {
	if pollInterval <= 0 {
		pollInterval = 2500 * time.Millisecond
	}
	if timeout <= 0 {
		timeout = 10 * time.Minute
	}
	deadline := time.Now().Add(timeout)
	for {
		task, err := s.GetTask(ctx, id)
		if err != nil {
			return nil, err
		}
		switch task.Status {
		case "completed":
			return task, nil
		case "failed", "expired":
			return nil, &APIError{Code: task.Status, Message: "video task " + id + " ended with status " + task.Status}
		}
		if time.Now().After(deadline) {
			return nil, &APIError{Code: "wait_timeout", Message: "timed out waiting for video task " + id}
		}
		if !sleepCtx(ctx, pollInterval) {
			return nil, ctx.Err()
		}
	}
}

// GenerateAndWait creates a task and waits for completion.
func (s *VideoService) GenerateAndWait(ctx context.Context, params VideoParams, pollInterval, timeout time.Duration) (*VideoTask, error) {
	task, err := s.Generate(ctx, params)
	if err != nil {
		return nil, err
	}
	return s.WaitForCompletion(ctx, task.TaskID, pollInterval, timeout)
}

// --- voices (cloning) --------------------------------------------------------

// VoiceSample is one audio sample for cloning.
type VoiceSample struct {
	Filename string
	Data     []byte
}

// VoicesService accesses /v1/voices.
type VoicesService struct{ client *Client }

// ConsentText returns the current consent paragraph and its hash.
func (s *VoicesService) ConsentText(ctx context.Context) (map[string]any, error) {
	var out map[string]any
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/voices/consent-text", requestOptions{auth: "none"}, &out)
	return out, err
}

// Clone creates a cloned voice from one or more samples.
func (s *VoicesService) Clone(ctx context.Context, name, consentHash string, samples []VoiceSample, extra map[string]string) (map[string]any, error) {
	fields := map[string]string{"name": name, "consent_hash": consentHash}
	for k, v := range extra {
		fields[k] = v
	}
	files := make([]fileEntry, 0, len(samples))
	for _, sample := range samples {
		files = append(files, fileEntry{"files", sample.Filename, sample.Data})
	}
	body, ct, err := buildMultipart(fields, files)
	if err != nil {
		return nil, err
	}
	var out map[string]any
	err = s.client.requestJSON(ctx, http.MethodPost, "/v1/voices/clone", requestOptions{auth: "api_key", body: body, contentType: ct}, &out)
	return out, err
}

// Library lists the caller's cloned voices.
func (s *VoicesService) Library(ctx context.Context) ([]map[string]any, error) {
	var out struct {
		Voices []map[string]any `json:"voices"`
	}
	err := s.client.requestJSON(ctx, http.MethodGet, "/v1/voices/library", requestOptions{auth: "api_key"}, &out)
	return out.Voices, err
}

// Update renames or re-describes a cloned voice.
func (s *VoicesService) Update(ctx context.Context, voiceID string, body map[string]any) (map[string]any, error) {
	var out map[string]any
	err := s.client.postJSONMethod(ctx, http.MethodPatch, "/v1/voices/clone/"+url.PathEscape(voiceID), "api_key", body, &out)
	return out, err
}

// Delete removes a cloned voice.
func (s *VoicesService) Delete(ctx context.Context, voiceID string) (map[string]any, error) {
	var out map[string]any
	err := s.client.requestJSON(ctx, http.MethodDelete, "/v1/voices/clone/"+url.PathEscape(voiceID), requestOptions{auth: "api_key"}, &out)
	return out, err
}
