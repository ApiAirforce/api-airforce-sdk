package airforce

import (
	"bufio"
	"encoding/json"
	"io"
	"net/http"
	"strings"
)

// Stream is a typed iterator over Server-Sent Events. Usage:
//
//	stream, err := client.Chat.CreateStream(ctx, params)
//	if err != nil { ... }
//	defer stream.Close()
//	for stream.Next() {
//	    chunk := stream.Current()
//	    ...
//	}
//	if err := stream.Err(); err != nil { ... }
type Stream[T any] struct {
	resp   *http.Response
	reader *bufio.Reader
	cur    T
	err    error
	done   bool
}

func newStream[T any](resp *http.Response) *Stream[T] {
	return &Stream[T]{resp: resp, reader: bufio.NewReader(resp.Body)}
}

// Next advances to the next event, returning false at end of stream or on error.
func (s *Stream[T]) Next() bool {
	if s.done {
		return false
	}
	var data []string
	for {
		line, err := s.reader.ReadString('\n')
		if err != nil {
			if err == io.EOF && len(data) > 0 {
				return s.emit(data)
			}
			if err != io.EOF {
				s.err = err
			}
			s.finish()
			return false
		}
		line = strings.TrimRight(line, "\r\n")
		if line == "" {
			if len(data) == 0 {
				continue
			}
			return s.emit(data)
		}
		if strings.HasPrefix(line, ":") {
			continue // comment / keep-alive
		}
		if value, ok := strings.CutPrefix(line, "data:"); ok {
			data = append(data, strings.TrimPrefix(value, " "))
		}
	}
}

func (s *Stream[T]) emit(data []string) bool {
	payload := strings.Join(data, "\n")
	if payload == "[DONE]" {
		s.finish()
		return false
	}
	var v T
	if err := json.Unmarshal([]byte(payload), &v); err != nil {
		s.err = err
		s.finish()
		return false
	}
	s.cur = v
	return true
}

func (s *Stream[T]) finish() {
	s.done = true
	s.Close()
}

// Current returns the most recent event decoded by Next.
func (s *Stream[T]) Current() T { return s.cur }

// Err returns the first error encountered during iteration, if any.
func (s *Stream[T]) Err() error { return s.err }

// Close releases the underlying HTTP connection.
func (s *Stream[T]) Close() error {
	if s.resp != nil && s.resp.Body != nil {
		return s.resp.Body.Close()
	}
	return nil
}
