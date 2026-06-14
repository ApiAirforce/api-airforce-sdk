package airforce

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
)

// ErrMissingCredential is returned when an endpoint needs a credential that was
// not configured (api key or session token).
var ErrMissingCredential = errors.New("airforce: missing credential for this endpoint")

// APIError is returned for any non-2xx HTTP response.
type APIError struct {
	Status     int
	Code       string
	Type       string
	Message    string
	Param      string
	RequestID  string
	RetryAfter float64 // seconds, for 429 responses
	Body       []byte
}

func (e *APIError) Error() string {
	if e.Code != "" {
		return fmt.Sprintf("airforce: HTTP %d: %s (%s)", e.Status, e.Message, e.Code)
	}
	return fmt.Sprintf("airforce: HTTP %d: %s", e.Status, e.Message)
}

// IsStatus reports whether err is an *APIError with the given HTTP status.
func IsStatus(err error, status int) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr) && apiErr.Status == status
}

func (e *APIError) IsBadRequest() bool          { return e.Status == http.StatusBadRequest }
func (e *APIError) IsAuthentication() bool      { return e.Status == http.StatusUnauthorized }
func (e *APIError) IsInsufficientBalance() bool { return e.Status == http.StatusPaymentRequired }
func (e *APIError) IsPermissionDenied() bool    { return e.Status == http.StatusForbidden }
func (e *APIError) IsNotFound() bool            { return e.Status == http.StatusNotFound }
func (e *APIError) IsConflict() bool            { return e.Status == http.StatusConflict }
func (e *APIError) IsRateLimited() bool         { return e.Status == http.StatusTooManyRequests }
func (e *APIError) IsServerError() bool         { return e.Status >= 500 }

func parseAPIError(status int, body []byte, header http.Header) *APIError {
	apiErr := &APIError{Status: status, Body: body, RequestID: header.Get("x-request-id")}

	var envelope struct {
		Error   json.RawMessage `json:"error"`
		Message string          `json:"message"`
		Code    string          `json:"code"`
		Type    string          `json:"type"`
	}
	if json.Unmarshal(body, &envelope) == nil {
		var nested struct {
			Message string `json:"message"`
			Code    string `json:"code"`
			Type    string `json:"type"`
			Param   string `json:"param"`
		}
		if len(envelope.Error) > 0 && json.Unmarshal(envelope.Error, &nested) == nil && nested.Message != "" {
			apiErr.Message, apiErr.Code, apiErr.Type, apiErr.Param = nested.Message, nested.Code, nested.Type, nested.Param
		} else {
			var flat string
			if json.Unmarshal(envelope.Error, &flat) == nil && flat != "" {
				apiErr.Message = flat
			} else {
				apiErr.Message = envelope.Message
			}
			apiErr.Code, apiErr.Type = envelope.Code, envelope.Type
		}
	}
	if apiErr.Message == "" {
		apiErr.Message = fmt.Sprintf("Airforce API error (HTTP %d)", status)
	}
	if ra := header.Get("retry-after"); ra != "" {
		if secs, err := strconv.ParseFloat(ra, 64); err == nil {
			apiErr.RetryAfter = secs
		}
	}
	return apiErr
}
