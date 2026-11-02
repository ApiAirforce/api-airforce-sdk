package airforce

import (
	"context"
	"net/http"
	"strconv"
)

// ImageFile is one file for Images.Edit: an input image or the mask.
type ImageFile struct {
	Name string
	Data []byte
}

// ImageEditParams is the request for Images.Edit (multipart POST
// /v1/images/edits). Images needs at least one entry and at most 16, 25 MB
// each. Mask is forwarded as is; no listed model declares mask support.
type ImageEditParams struct {
	Model          string
	Prompt         string
	Images         []ImageFile
	Mask           *ImageFile
	N              int
	Size           string
	AspectRatio    string
	Quality        string
	ResponseFormat string

	// Extra carries any other form field, sent as given.
	Extra map[string]string
}

// Edit edits or varies the input image(s). Same models, prices and response
// shape as Generate.
func (s *ImagesService) Edit(ctx context.Context, params ImageEditParams) (*ImagesResponse, error) {
	fields := map[string]string{"model": params.Model, "prompt": params.Prompt}
	if params.N > 0 {
		fields["n"] = strconv.Itoa(params.N)
	}
	for k, v := range map[string]string{
		"size":            params.Size,
		"aspect_ratio":    params.AspectRatio,
		"quality":         params.Quality,
		"response_format": params.ResponseFormat,
	} {
		if v != "" {
			fields[k] = v
		}
	}
	for k, v := range params.Extra {
		fields[k] = v
	}
	files := make([]fileEntry, 0, len(params.Images)+1)
	for _, img := range params.Images {
		files = append(files, fileEntry{"image", img.Name, img.Data})
	}
	if params.Mask != nil {
		files = append(files, fileEntry{"mask", params.Mask.Name, params.Mask.Data})
	}
	body, ct, err := buildMultipart(fields, files)
	if err != nil {
		return nil, err
	}
	var out ImagesResponse
	err = s.client.requestJSON(ctx, http.MethodPost, "/v1/images/edits", requestOptions{auth: "api_key", body: body, contentType: ct}, &out)
	return &out, err
}
