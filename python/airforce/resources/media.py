"""Media resources: images, audio, video, and voice cloning."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .._exceptions import AirforceError
from ._base import AsyncAPIResource, SyncAPIResource, clean, enc

FileContent = Any  # bytes | file-like, per httpx
_TERMINAL = {"completed", "failed", "expired"}


def _form(fields: Dict[str, Any]) -> Dict[str, str]:
    """Stringify form fields (JSON-encode non-strings) for multipart bodies."""
    out: Dict[str, str] = {}
    for key, value in clean(**fields).items():
        out[key] = value if isinstance(value, str) else json.dumps(value)
    return out


# --- Images ------------------------------------------------------------------

class Images(SyncAPIResource):
    def generate(self, *, model: str, prompt: str, **params: Any) -> Any:
        """Generate image(s). Optional: n, size, quality, response_format,
        aspect_ratio, input_images, ``models`` (fallback)."""
        return self._transport.request(
            "POST", "/v1/images/generations", json={"model": model, "prompt": prompt, **clean(**params)}
        )


class AsyncImages(AsyncAPIResource):
    async def generate(self, *, model: str, prompt: str, **params: Any) -> Any:
        return await self._transport.request(
            "POST", "/v1/images/generations", json={"model": model, "prompt": prompt, **clean(**params)}
        )


# --- Audio -------------------------------------------------------------------

class Audio(SyncAPIResource):
    def speech(self, *, model: str, input: str, voice: str, **params: Any) -> bytes:
        return self._transport.request_binary(
            "POST", "/v1/audio/speech", json={"model": model, "input": input, "voice": voice, **clean(**params)}
        )

    def music(self, *, model: str, prompt: str, **params: Any) -> bytes:
        return self._transport.request_binary(
            "POST", "/v1/audio/music", json={"model": model, "prompt": prompt, **clean(**params)}
        )

    def sound_effects(self, *, model: str, prompt: str, **params: Any) -> bytes:
        return self._transport.request_binary(
            "POST", "/v1/audio/sound-effects", json={"model": model, "prompt": prompt, **clean(**params)}
        )

    def transcriptions(self, *, model: str, file: FileContent, filename: str = "file", **params: Any) -> Any:
        return self._transport.request(
            "POST", "/v1/audio/transcriptions",
            data=_form({"model": model, **params}), files={"file": (filename, file)},
        )

    def audio_isolation(self, *, model: str, file: FileContent, filename: str = "file", **params: Any) -> bytes:
        return self._transport.request_binary(
            "POST", "/v1/audio/audio-isolation",
            data=_form({"model": model, **params}), files={"file": (filename, file)},
        )

    def voice_changer(self, *, model: str, file: FileContent, voice: str, filename: str = "file", **params: Any) -> bytes:
        return self._transport.request_binary(
            "POST", "/v1/audio/voice-changer",
            data=_form({"model": model, "voice": voice, **params}), files={"file": (filename, file)},
        )

    def dubbing(self, *, model: str, file: FileContent, target_lang: str, filename: str = "file", **params: Any) -> Any:
        return self._transport.request(
            "POST", "/v1/audio/dubbing",
            data=_form({"model": model, "target_lang": target_lang, **params}), files={"file": (filename, file)},
        )

    def dubbing_status(self, dubbing_id: str, **kw: Any) -> Any:
        return self._transport.request("GET", f"/v1/audio/dubbing/{enc(dubbing_id)}", **kw)

    def dubbing_audio(self, dubbing_id: str, lang: str, **kw: Any) -> bytes:
        return self._transport.request_binary("GET", f"/v1/audio/dubbing/{enc(dubbing_id)}/audio/{enc(lang)}", **kw)

    def voices(self, **kw: Any) -> List[Any]:
        res = self._transport.request("GET", "/v1/audio/voices", **kw)
        return res.get("voices", []) if isinstance(res, dict) else res


class AsyncAudio(AsyncAPIResource):
    async def speech(self, *, model: str, input: str, voice: str, **params: Any) -> bytes:
        return await self._transport.request_binary(
            "POST", "/v1/audio/speech", json={"model": model, "input": input, "voice": voice, **clean(**params)}
        )

    async def music(self, *, model: str, prompt: str, **params: Any) -> bytes:
        return await self._transport.request_binary(
            "POST", "/v1/audio/music", json={"model": model, "prompt": prompt, **clean(**params)}
        )

    async def sound_effects(self, *, model: str, prompt: str, **params: Any) -> bytes:
        return await self._transport.request_binary(
            "POST", "/v1/audio/sound-effects", json={"model": model, "prompt": prompt, **clean(**params)}
        )

    async def transcriptions(self, *, model: str, file: FileContent, filename: str = "file", **params: Any) -> Any:
        return await self._transport.request(
            "POST", "/v1/audio/transcriptions",
            data=_form({"model": model, **params}), files={"file": (filename, file)},
        )

    async def audio_isolation(self, *, model: str, file: FileContent, filename: str = "file", **params: Any) -> bytes:
        return await self._transport.request_binary(
            "POST", "/v1/audio/audio-isolation",
            data=_form({"model": model, **params}), files={"file": (filename, file)},
        )

    async def voice_changer(self, *, model: str, file: FileContent, voice: str, filename: str = "file", **params: Any) -> bytes:
        return await self._transport.request_binary(
            "POST", "/v1/audio/voice-changer",
            data=_form({"model": model, "voice": voice, **params}), files={"file": (filename, file)},
        )

    async def dubbing(self, *, model: str, file: FileContent, target_lang: str, filename: str = "file", **params: Any) -> Any:
        return await self._transport.request(
            "POST", "/v1/audio/dubbing",
            data=_form({"model": model, "target_lang": target_lang, **params}), files={"file": (filename, file)},
        )

    async def dubbing_status(self, dubbing_id: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/v1/audio/dubbing/{enc(dubbing_id)}", **kw)

    async def dubbing_audio(self, dubbing_id: str, lang: str, **kw: Any) -> bytes:
        return await self._transport.request_binary("GET", f"/v1/audio/dubbing/{enc(dubbing_id)}/audio/{enc(lang)}", **kw)

    async def voices(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/v1/audio/voices", **kw)
        return res.get("voices", []) if isinstance(res, dict) else res


# --- Video -------------------------------------------------------------------

class Video(SyncAPIResource):
    def generate(self, *, model: str, prompt: str, **params: Any) -> Any:
        """Create an async video task. Optional: mode, duration_seconds,
        aspect_ratio, quality, input_images."""
        return self._transport.request(
            "POST", "/v1/video/generations", json={"model": model, "prompt": prompt, **clean(**params)}
        )

    def get_task(self, task_id: str, **kw: Any) -> Any:
        return self._transport.request("GET", f"/v1/video/tasks/{enc(task_id)}", **kw)

    def list_tasks(self, **kw: Any) -> List[Any]:
        res = self._transport.request("GET", "/v1/video/tasks", **kw)
        return res.get("data", []) if isinstance(res, dict) else res

    def delete_task(self, task_id: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/v1/video/tasks/{enc(task_id)}", **kw)

    def wait_for_completion(self, task_id: str, *, poll_interval: float = 2.5, timeout: float = 600.0, **kw: Any) -> Any:
        deadline = time.monotonic() + timeout
        while True:
            task = self.get_task(task_id, **kw)
            status = task.get("status")
            if status in _TERMINAL:
                if status != "completed":
                    raise AirforceError(f"Video task {task_id} ended with status '{status}'", code=status, body=task)
                return task
            if time.monotonic() > deadline:
                raise AirforceError(f"Timed out waiting for video task {task_id}", code="wait_timeout", body=task)
            time.sleep(poll_interval)

    def generate_and_wait(self, *, model: str, prompt: str, poll_interval: float = 2.5, timeout: float = 600.0, **params: Any) -> Any:
        task = self.generate(model=model, prompt=prompt, **params)
        return self.wait_for_completion(task["task_id"], poll_interval=poll_interval, timeout=timeout)


class AsyncVideo(AsyncAPIResource):
    async def generate(self, *, model: str, prompt: str, **params: Any) -> Any:
        return await self._transport.request(
            "POST", "/v1/video/generations", json={"model": model, "prompt": prompt, **clean(**params)}
        )

    async def get_task(self, task_id: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/v1/video/tasks/{enc(task_id)}", **kw)

    async def list_tasks(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/v1/video/tasks", **kw)
        return res.get("data", []) if isinstance(res, dict) else res

    async def delete_task(self, task_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/v1/video/tasks/{enc(task_id)}", **kw)

    async def wait_for_completion(self, task_id: str, *, poll_interval: float = 2.5, timeout: float = 600.0, **kw: Any) -> Any:
        deadline = time.monotonic() + timeout
        while True:
            task = await self.get_task(task_id, **kw)
            status = task.get("status")
            if status in _TERMINAL:
                if status != "completed":
                    raise AirforceError(f"Video task {task_id} ended with status '{status}'", code=status, body=task)
                return task
            if time.monotonic() > deadline:
                raise AirforceError(f"Timed out waiting for video task {task_id}", code="wait_timeout", body=task)
            await asyncio.sleep(poll_interval)

    async def generate_and_wait(self, *, model: str, prompt: str, poll_interval: float = 2.5, timeout: float = 600.0, **params: Any) -> Any:
        task = await self.generate(model=model, prompt=prompt, **params)
        return await self.wait_for_completion(task["task_id"], poll_interval=poll_interval, timeout=timeout)


# --- Voices (cloning) --------------------------------------------------------

def _clone_files(samples: Sequence[Tuple[FileContent, str]]) -> List[Tuple[str, Tuple[str, FileContent]]]:
    return [("files", (name, content)) for content, name in samples]


class Voices(SyncAPIResource):
    def consent_text(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/v1/voices/consent-text", auth="none", **kw)

    def clone(self, *, name: str, consent_hash: str, samples: Sequence[Tuple[FileContent, str]], **params: Any) -> Any:
        return self._transport.request(
            "POST", "/v1/voices/clone",
            data=_form({"name": name, "consent_hash": consent_hash, **params}),
            files=_clone_files(samples),
        )

    def library(self, **kw: Any) -> List[Any]:
        res = self._transport.request("GET", "/v1/voices/library", **kw)
        return res.get("voices", []) if isinstance(res, dict) else res

    def update(self, voice_id: str, *, name: Optional[str] = None, description: Optional[str] = None, **kw: Any) -> Any:
        return self._transport.request("PATCH", f"/v1/voices/clone/{enc(voice_id)}", json=clean(name=name, description=description), **kw)

    def delete(self, voice_id: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/v1/voices/clone/{enc(voice_id)}", **kw)


class AsyncVoices(AsyncAPIResource):
    async def consent_text(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/v1/voices/consent-text", auth="none", **kw)

    async def clone(self, *, name: str, consent_hash: str, samples: Sequence[Tuple[FileContent, str]], **params: Any) -> Any:
        return await self._transport.request(
            "POST", "/v1/voices/clone",
            data=_form({"name": name, "consent_hash": consent_hash, **params}),
            files=_clone_files(samples),
        )

    async def library(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/v1/voices/library", **kw)
        return res.get("voices", []) if isinstance(res, dict) else res

    async def update(self, voice_id: str, *, name: Optional[str] = None, description: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("PATCH", f"/v1/voices/clone/{enc(voice_id)}", json=clean(name=name, description=description), **kw)

    async def delete(self, voice_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/v1/voices/clone/{enc(voice_id)}", **kw)
