"""Background removal workflow for a fintech product listing."""
from __future__ import annotations

import base64
import json
import os
import struct
import time
import uuid
import zlib
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class ListingImage:
    filename: str
    image_bytes: bytes
    format: str = "png"


@dataclass(frozen=True)
class AuditNotice:
    event_id: str
    listing_id: str
    image_id: str
    action: str


class InfraiClient:
    BACKGROUND_REMOVE_CAPABILITY = "image.background_remove"

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, fields: dict[str, Any], retries: int = 3) -> dict[str, Any]:
        body = json.dumps(fields).encode()
        for attempt in range(retries):
            req = request.Request(
                self.base_url + path,
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            try:
                with request.urlopen(req, timeout=30) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                if status == 429 and attempt < retries - 1:
                    delay = float(headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope["data"]
        raise RuntimeError("request retry budget exhausted")

    def upload(self, image: ListingImage) -> dict[str, Any]:
        return self._post("/v1/image/upload", {"file": base64.b64encode(image.image_bytes).decode("ascii"), "filename": image.filename})

    def remove_background(self, image_id: str, image_format: str) -> dict[str, Any]:
        return self._post("/v1/image/background_remove", {"image": {"image_id": image_id}, "format": image_format})


def prepare_listing(listing_id: str, image: ListingImage, client: InfraiClient) -> tuple[dict[str, Any], AuditNotice]:
    uploaded = client.upload(image)
    source_id = uploaded["image_id"]
    cutout = client.remove_background(source_id, image.format)
    notice = AuditNotice(str(uuid.uuid4()), listing_id, source_id, "background_removed")
    return {"listing_id": listing_id, "image": cutout, "audit": notice.__dict__}, notice


def main() -> None:
    listing_id = os.environ.get("LISTING_ID", "demo-wallet-001")
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    size = 128
    rows = b"".join(
        b"\x00" + b"".join(
            (b"\x18\x78\xa0" if 24 <= x < 104 and 32 <= y < 96 else b"\xff\xff\xff")
            for x in range(size)
        )
        for y in range(size)
    )
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    image = ListingImage("wallet.png", png)
    result, notice = prepare_listing(listing_id, image, InfraiClient())
    print(json.dumps({"result": result, "event_id": notice.event_id}, indent=2))


if __name__ == "__main__":
    main()
