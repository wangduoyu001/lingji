from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from ..base import ExtractionAdapter
from ..models import ExtractedDocument, ExtractionBatch, ExtractionRequest
from ..privacy import PrivacyClassifier


TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "spm",
    "from",
    "share_source",
    "share_token",
}


class _ReadableHTMLParser(HTMLParser):
    BLOCKED = {"script", "style", "noscript", "svg", "canvas"}
    TEXT_TAGS = {"p", "article", "section", "main", "h1", "h2", "h3", "h4", "li", "blockquote", "pre"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.text_parts: list[str] = []
        self._blocked_depth = 0
        self._in_title = False
        self._capture_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag in self.BLOCKED:
            self._blocked_depth += 1
            return
        if self._blocked_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (
                attrs_dict.get("property")
                or attrs_dict.get("name")
                or attrs_dict.get("itemprop")
            ).strip().lower()
            value = attrs_dict.get("content", "").strip()
            if key and value:
                self.meta[key] = value
        if tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            href = attrs_dict.get("href", "").strip()
            if rel and href:
                self.links[rel] = href
        if tag in self.TEXT_TAGS:
            self._capture_text = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.BLOCKED and self._blocked_depth:
            self._blocked_depth -= 1
            return
        if self._blocked_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in self.TEXT_TAGS:
            self._capture_text = False
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._blocked_depth:
            return
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        if self._in_title:
            self.title = (self.title + " " + value).strip()
        if self._capture_text:
            self.text_parts.append(value)

    def text(self) -> str:
        raw = " ".join(self.text_parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\s*\n\s*", "\n", raw)
        return raw.strip()


class WebCaptureAdapter(ExtractionAdapter):
    """Capture browser snapshots and safely fetch simple public pages when allowed.

    Dynamic/login-only platforms should submit rendered HTML/text through a browser
    extension or Playwright capture. This adapter never steals browser credentials.
    """

    name = "web_capture"
    version = "1.0.0"
    source_types = (
        "web",
        "browser",
        "wechat_article",
        "video_channel",
        "douyin",
        "xiaohongshu",
    )

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        if source_type not in self.source_types:
            return False
        if payload.get("url") or payload.get("html") or payload.get("text"):
            return True
        return bool(input_path and input_path.suffix.lower() in {".html", ".htm", ".json", ".txt", ".md"})

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        data = self._load_capture(request)
        url = self._clean_url(str(data.get("url") or data.get("source_url") or ""))
        platform, source_type = self._platform(url, request.source_type, data)
        page_html = str(data.get("html") or "")
        parsed = self._parse_html(page_html) if page_html else {}
        title = self._first(
            data.get("title"),
            parsed.get("og:title"),
            parsed.get("twitter:title"),
            parsed.get("title"),
            "未命名网页",
        )
        author = self._first(
            data.get("author"),
            data.get("account_name"),
            parsed.get("author"),
            parsed.get("article:author"),
            parsed.get("og:site_name"),
        )
        description = self._first(
            data.get("description"),
            parsed.get("og:description"),
            parsed.get("description"),
            parsed.get("twitter:description"),
        )
        canonical_url = self._clean_url(
            self._first(data.get("canonical_url"), parsed.get("canonical"), url)
        )
        text = self._first(
            data.get("selected_text"),
            data.get("text"),
            data.get("content"),
            parsed.get("text"),
        )
        transcript = self._as_text(data.get("transcript"))
        ocr_text = self._as_text(data.get("ocr_text"))
        published_at = self._first(
            data.get("published_at"),
            data.get("publish_time"),
            parsed.get("article:published_time"),
            parsed.get("date"),
        )
        duration = self._first(
            data.get("duration_seconds"),
            data.get("duration"),
            parsed.get("video:duration"),
        )
        cover_url = self._first(
            data.get("cover_url"),
            data.get("thumbnail_url"),
            parsed.get("og:image"),
            parsed.get("twitter:image"),
        )
        media_url = self._first(data.get("media_url"), data.get("local_media_path"))
        external_id = self._first(data.get("external_id"), data.get("video_id"), canonical_url, url)
        stable_material = external_id or json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
        stable_id = "LJ-WEB-" + hashlib.sha256(stable_material.encode("utf-8")).hexdigest()[:24].upper()
        body = self._render(
            title=title,
            url=canonical_url or url,
            platform=platform,
            author=author,
            description=description,
            published_at=str(published_at or ""),
            duration=str(duration or ""),
            cover_url=cover_url,
            media_url=media_url,
            text=text,
            transcript=transcript,
            ocr_text=ocr_text,
            extra=data,
        )
        assessment = PrivacyClassifier().assess(
            body,
            request.options.get("sensitive_terms") or (),
        )
        destination = "private_source" if assessment.restricted else "source_archive"
        metadata = {
            "source_url": canonical_url or url,
            "platform": platform,
            "author": author,
            "account_name": self._first(data.get("account_name"), author),
            "published_at": published_at,
            "duration_seconds": duration,
            "cover_url": cover_url,
            "media_url": media_url,
            "capture_method": self._first(data.get("capture_method"), "browser_snapshot" if page_html else "payload"),
            "content_completeness": self._completeness(text, transcript, page_html),
            "privacy": assessment.privacy,
            "sensitivity_findings": assessment.kinds(),
            "project": request.options.get("project_id") or request.options.get("project") or [],
            "tags": [f"source/{source_type}", f"topic/{platform}"],
            "status": "active" if text or transcript else "needs_review",
            "review_status": "needs_review" if not text and not transcript else "",
        }
        warnings = []
        if not text and not transcript:
            warnings.append("页面正文未取得，仅保存元数据；需要浏览器快照、录屏或本地媒体补充")
        if platform == "video_channel" and not transcript and not media_url:
            warnings.append("视频号公开分享页可能不包含完整正文或媒体地址，当前按降级模式保存")
        return ExtractionBatch(
            documents=(
                ExtractedDocument(
                    stable_id=stable_id,
                    title=title,
                    body=body,
                    source_type=source_type,
                    destination=destination,
                    external_id=str(external_id or ""),
                    created_at=str(published_at or ""),
                    updated_at=str(data.get("captured_at") or ""),
                    metadata=metadata,
                ),
            ),
            summary={
                "platform": platform,
                "source_type": source_type,
                "content_completeness": metadata["content_completeness"],
                "restricted": assessment.restricted,
            },
            warnings=tuple(warnings),
        )

    def _load_capture(self, request: ExtractionRequest) -> dict[str, Any]:
        data = dict(request.payload or {})
        if request.input_path:
            path = request.input_path
            suffix = path.suffix.lower()
            if suffix == ".json":
                loaded = json.loads(path.read_text(encoding="utf-8-sig"))
                if not isinstance(loaded, dict):
                    raise ValueError("Web capture JSON must be an object")
                data = {**loaded, **data}
            elif suffix in {".html", ".htm"}:
                data.setdefault("html", path.read_text(encoding="utf-8-sig"))
            else:
                data.setdefault("text", path.read_text(encoding="utf-8-sig"))
        url = str(data.get("url") or data.get("source_url") or "")
        if url and not data.get("html") and not data.get("text") and request.options.get("allow_network_fetch"):
            data.update(self._fetch_public_page(url, request.options))
        return data

    def _fetch_public_page(self, url: str, options: Mapping[str, Any]) -> dict[str, Any]:
        cleaned = self._clean_url(url)
        self._assert_public_url(cleaned)
        timeout = float(options.get("network_timeout_seconds", 15))
        max_bytes = int(options.get("max_response_bytes", 8 * 1024 * 1024))
        response = requests.get(
            cleaned,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
            headers={"User-Agent": "LingJiCapture/1.0 (+local personal knowledge system)"},
        )
        response.raise_for_status()
        self._assert_public_url(response.url)
        chunks = []
        size = 0
        for chunk in response.iter_content(64 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("Web response exceeds configured size limit")
            chunks.append(chunk)
        encoding = response.encoding or response.apparent_encoding or "utf-8"
        return {
            "url": response.url,
            "html": b"".join(chunks).decode(encoding, errors="replace"),
            "capture_method": "server_fetch",
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type", ""),
        }

    @staticmethod
    def _assert_public_url(url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only public http/https URLs are supported")
        host = parsed.hostname.lower()
        if host in {"localhost", "localhost.localdomain"}:
            raise PermissionError("Local URLs are blocked")
        try:
            addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        except socket.gaierror as exc:
            raise ValueError(f"Unable to resolve host: {host}") from exc
        for item in addresses:
            address = ipaddress.ip_address(item[4][0])
            if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
                raise PermissionError(f"Private network address is blocked: {address}")

    @staticmethod
    def _parse_html(raw_html: str) -> dict[str, str]:
        parser = _ReadableHTMLParser()
        parser.feed(raw_html)
        result = dict(parser.meta)
        result["title"] = html.unescape(parser.title)
        result["text"] = html.unescape(parser.text())
        if "canonical" in parser.links:
            result["canonical"] = parser.links["canonical"]
        return result

    @staticmethod
    def _platform(url: str, requested: str, data: Mapping[str, Any]) -> tuple[str, str]:
        hinted = str(data.get("platform") or "").strip().lower().replace("-", "_")
        if hinted in {"video_channel", "wechat_channels", "视频号"} or requested == "video_channel":
            return "video_channel", "video_channel"
        host = (urlsplit(url).hostname or "").lower()
        if "mp.weixin.qq.com" in host or requested == "wechat_article":
            return "wechat_article", "wechat_article"
        if "channels.weixin.qq.com" in host:
            return "video_channel", "video_channel"
        if "douyin.com" in host or "iesdouyin.com" in host or requested == "douyin":
            return "douyin", "douyin"
        if "xiaohongshu.com" in host or "xhslink.com" in host or requested == "xiaohongshu":
            return "xiaohongshu", "xiaohongshu"
        if "bilibili.com" in host:
            return "bilibili", "web"
        if "youtube.com" in host or host == "youtu.be":
            return "youtube", "web"
        return hinted or "website", "web"

    @staticmethod
    def _render(**values: Any) -> str:
        lines = [f"# {values['title']}", "", "## 来源信息", ""]
        fields = (
            ("平台", values["platform"]),
            ("网址", values["url"]),
            ("作者/账号", values["author"]),
            ("发布时间", values["published_at"]),
            ("时长", values["duration"]),
            ("封面", values["cover_url"]),
            ("媒体", values["media_url"]),
        )
        for label, value in fields:
            if value not in (None, ""):
                lines.append(f"- {label}：{value}")
        if values["description"]:
            lines.extend(["", "## 简介", "", str(values["description"])])
        if values["text"]:
            lines.extend(["", "## 页面正文", "", str(values["text"])])
        if values["transcript"]:
            lines.extend(["", "## 视频/音频转写", "", str(values["transcript"])])
        if values["ocr_text"]:
            lines.extend(["", "## 画面文字 OCR", "", str(values["ocr_text"])])
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _completeness(text: str, transcript: str, raw_html: str) -> str:
        if transcript and text:
            return "full"
        if transcript or len(text or "") >= 500:
            return "content"
        if raw_html or text:
            return "partial"
        return "metadata_only"

    @staticmethod
    def _first(*values: Any) -> str:
        for value in values:
            if value not in (None, "", [], {}):
                return str(value).strip()
        return ""

    @staticmethod
    def _as_text(value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)

    @staticmethod
    def _clean_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlsplit(url.strip())
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith("utm_")
        ]
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
