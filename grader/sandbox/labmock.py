"""The NeuroMind practice API, simulated in-process. ONE file used by both runtimes (the browser's Python and the grading sandbox),
so a learner's program gets the same answer in practice and in official grading, with no network anywhere.

Base URL: https://api.neuromind.lab/v1   Test key: nm-test-key-123 (send it as `Authorization: Bearer ...`).
`install()` mounts an adapter on every `requests.Session` so that real `requests` code works against this host and every
other host raises ConnectionError. Everything is deterministic: the same input always gives the same output.
Documented for authors in docs/01-product/PRACTICAL_LABS_SPEC.md §6.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

HOST = "api.neuromind.lab"
BASE_URL = f"https://{HOST}/v1"
TEST_KEY = "nm-test-key-123"
VERSION = "1.0"

# ---------------------------------------------------------------- fixed data
CITIES = ["Pune", "Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Jaipur", "London", "Tokyo", "Nairobi", "Toronto"]
CONDITIONS = ["sunny", "cloudy", "light rain", "humid", "clear", "windy"]
BOOKS = [
    {"id": 1, "title": "Python for Everyone", "author": "Asha Rao", "year": 2021, "pages": 320, "genre": "programming"},
    {"id": 2, "title": "Data, Simply", "author": "Asha Rao", "year": 2023, "pages": 210, "genre": "data"},
    {"id": 3, "title": "The Thinking Machine", "author": "Bilal Khan", "year": 2019, "pages": 288, "genre": "ai"},
    {"id": 4, "title": "Monsoon Code", "author": "Tara Iyer", "year": 2022, "pages": 150, "genre": "fiction"},
    {"id": 5, "title": "Agents at Work", "author": "Bilal Khan", "year": 2024, "pages": 240, "genre": "ai"},
]
HEADLINES = [
    {"id": 101, "title": "City library opens a free coding corner for teenagers", "source": "Pune Daily", "published": "2026-10-01"},
    {"id": 102, "title": "Monsoon rainfall 12% above average this year, says weather office", "source": "National Wire", "published": "2026-10-02"},
    {"id": 103, "title": "Students build a flood-warning sensor from spare phone parts", "source": "Tech Today", "published": "2026-10-03"},
    {"id": 104, "title": "New bus route cuts the airport journey to 40 minutes", "source": "Metro News", "published": "2026-10-04"},
    {"id": 105, "title": "Local bakery wins national award for its millet bread", "source": "Food & Life", "published": "2026-10-05"},
]
QUOTES = [
    {"id": 1, "text": "Programs must be written for people to read, and only incidentally for machines to execute.", "author": "Harold Abelson"},
    {"id": 2, "text": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"id": 3, "text": "Simplicity is the soul of efficiency.", "author": "Austin Freeman"},
    {"id": 4, "text": "Make it work, make it right, make it fast.", "author": "Kent Beck"},
]
SEARCH_RESULTS = {
    "python": [{"title": "Python tutorial", "url": "https://docs.python.org/3/tutorial/", "snippet": "An informal introduction to Python."},
               {"title": "Python for beginners", "url": "https://example.edu/python", "snippet": "A gentle course."}],
    "rag": [{"title": "Retrieval-augmented generation explained", "url": "https://example.org/rag", "snippet": "Retrieve, then generate."}],
}
POSITIVE = {"good", "great", "excellent", "love", "loved", "amazing", "wonderful", "fantastic", "happy", "best", "enjoyed", "helpful", "friendly", "fast", "delicious", "recommend"}
NEGATIVE = {"bad", "terrible", "awful", "hate", "hated", "worst", "slow", "rude", "broken", "poor", "disappointing", "boring", "late", "cold", "never"}
PEOPLE = {"asha rao", "bilal khan", "tara iyer", "ravi kumar", "meera nair", "ada lovelace", "alan turing", "priya sharma"}
PLACES = {"pune", "mumbai", "delhi", "bengaluru", "chennai", "kolkata", "hyderabad", "jaipur", "london", "tokyo", "nairobi", "toronto", "india", "kenya", "japan", "paris"}
ORGS = {"neuromind", "tata", "infosys", "google", "nasa", "unesco", "who", "isro"}
SYNONYMS = {"vacation": "leave", "holiday": "leave", "annual": "leave", "leave": "leave", "pto": "leave", "sick": "illness", "ill": "illness", "unwell": "illness",
            "salary": "pay", "pay": "pay", "wage": "pay", "wages": "pay", "income": "pay", "car": "vehicle", "vehicle": "vehicle", "automobile": "vehicle",
            "doctor": "medical", "physician": "medical", "medical": "medical", "hospital": "medical", "dog": "pet", "puppy": "pet", "cat": "pet", "kitten": "pet", "pet": "pet",
            "learn": "study", "study": "study", "studying": "study", "revise": "study", "exam": "test", "test": "test", "quiz": "test", "python": "python", "code": "code", "program": "code",
            "programming": "code", "coding": "code", "rain": "weather", "weather": "weather", "monsoon": "weather", "sunny": "weather", "happy": "joy", "joy": "joy", "glad": "joy",
            "sad": "sorrow", "unhappy": "sorrow", "sorrow": "sorrow", "fast": "speed", "quick": "speed", "speed": "speed", "rapid": "speed", "big": "large", "large": "large", "huge": "large"}
IMAGES: dict[str, dict[str, Any]] = {
    "street_sign.png": {"labels": [{"label": "street", "score": 0.91}, {"label": "shop sign", "score": 0.84}, {"label": "car", "score": 0.62}],
                        "boxes": [{"label": "car", "box": [12, 140, 180, 230], "score": 0.88}, {"label": "person", "box": [200, 120, 250, 240], "score": 0.79}, {"label": "sign", "box": [60, 20, 220, 70], "score": 0.93}],
                        "text": "RAO & SONS BAKERY\nOPEN 7 AM - 9 PM", "caption": "A street with a bakery sign, a parked car and a person walking"},
    "notes_page.png": {"labels": [{"label": "document", "score": 0.95}, {"label": "handwriting", "score": 0.77}], "boxes": [],
                       "text": "Photosynthesis: plants use sunlight, water and CO2 to make glucose and oxygen.\nChlorophyll absorbs light.\nHappens in the chloroplast.",
                       "caption": "A page of handwritten science notes about photosynthesis"},
    "receipt.png": {"labels": [{"label": "receipt", "score": 0.97}, {"label": "paper", "score": 0.8}], "boxes": [],
                    "text": "NEUROMART\nMilk 2L  120\nBread  45\nEggs x12  84\nTOTAL  249", "caption": "A printed shop receipt with three items"},
    "cat.jpg": {"labels": [{"label": "cat", "score": 0.98}, {"label": "sofa", "score": 0.71}], "boxes": [{"label": "cat", "box": [40, 60, 300, 280], "score": 0.98}],
                "text": "", "caption": "A tabby cat sitting on a grey sofa"},
    "dog.jpg": {"labels": [{"label": "dog", "score": 0.96}, {"label": "grass", "score": 0.74}], "boxes": [{"label": "dog", "box": [20, 80, 280, 300], "score": 0.96}],
                "text": "", "caption": "A brown dog running on grass"},
}
_flaky_calls: dict[str, int] = {}
_quote_counter = [0]


def _h(s: str, mod: int) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16) % mod


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


# ---------------------------------------------------------------- helpers also usable as plain Python (tokeniser, vectors)
def tokenize(text: str) -> list[dict[str, Any]]:
    """A simple deterministic sub-word tokeniser: words up to 5 characters stay whole; longer words split into 4-character pieces
    marked with '##'. Token ids are stable hashes, so the same piece always gets the same id (Lecture 39)."""
    out = []
    for w in re.findall(r"\w+|[^\w\s]", text):
        pieces = [w] if len(w) <= 5 else [w[:4]] + ["##" + w[i:i + 4] for i in range(4, len(w), 4)]
        for p in pieces:
            out.append({"token": p, "id": 1000 + _h(p.lower(), 30000)})
    return out


def embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic bag-of-concepts vector: every word (mapped through a small synonym table) adds a hashed direction, so
    sentences that mean the same thing point the same way even with different wording (Lectures 47, 60-65)."""
    v = [0.0] * dim
    for w in _words(text):
        key = SYNONYMS.get(w, w)
        if key in {"the", "a", "an", "is", "are", "of", "to", "and", "in", "on", "for", "i", "my", "do", "how", "many", "days", "get"}:
            continue
        i = _h(key, dim)
        v[i] += 1.0
        v[(i * 7 + 3) % dim] += 0.5
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, 6) for x in v]


def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b, strict=False))
    da = math.sqrt(sum(x * x for x in a)) or 1.0
    db = math.sqrt(sum(x * x for x in b)) or 1.0
    return round(num / (da * db), 6)


class VectorIndex:
    """A tiny in-memory vector index (Lecture 61): add(id, vector, metadata) then query(vector, k) -> top-k by cosine."""

    def __init__(self) -> None:
        self._items: list[tuple[str, list[float], dict]] = []

    def add(self, item_id: str, vector: list[float], metadata: dict | None = None) -> None:
        self._items.append((str(item_id), list(vector), dict(metadata or {})))

    def __len__(self) -> int:
        return len(self._items)

    def query(self, vector: list[float], k: int = 3) -> list[dict[str, Any]]:
        scored = [{"id": i, "score": cosine(vector, v), "metadata": m} for i, v, m in self._items]
        scored.sort(key=lambda r: (-r["score"], r["id"]))
        return scored[:k]


def chunk_text(text: str, size: int = 200, overlap: int = 40) -> list[str]:
    """Character chunks with overlap, breaking at spaces where possible (Lecture 59 helper, optional)."""
    chunks, i = [], 0
    while i < len(text):
        end = min(len(text), i + size)
        if end < len(text):
            cut = text.rfind(" ", i, end)
            if cut > i + size // 2:
                end = cut
        chunks.append(text[i:end].strip())
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)
    return [c for c in chunks if c]


# ---------------------------------------------------------------- the simulated HTTP API
class MockHTTPError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


def _json_body(body: Any) -> dict:
    if body is None or body == b"" or body == "":
        return {}
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8", "replace")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except ValueError as exc:
            raise MockHTTPError(400, "Request body must be JSON") from exc
    return dict(body) if isinstance(body, dict) else {}


def _chat_reply(messages: list[dict], tools: list[dict] | None) -> dict[str, Any]:
    last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    text = str(last.get("content", "")) if last else ""
    low = text.lower()
    if tools:
        for t in tools:
            name = str(t.get("name") or t.get("function", {}).get("name", ""))
            hints = set(_words(name)) | set(_words(str(t.get("description", ""))))
            numbers = re.findall(r"-?\d+(?:\.\d+)?", text)
            if ("calculat" in name or "math" in hints) and (len(numbers) >= 2 or any(op in low for op in ("plus", "times", "minus", "divided", "+", "*", "-", "/"))):
                return {"tool_calls": [{"name": name, "arguments": {"expression": re.sub(r"[^0-9+\-*/(). ]", "", text).strip() or " ".join(numbers)}}]}
            if "convert" in name and numbers and any(u in low for u in ("km", "mile", "kg", "pound", "celsius", "fahrenheit", "cm", "inch")):
                return {"tool_calls": [{"name": name, "arguments": {"value": float(numbers[0]), "text": text}}]}
            if ("search" in name or "lookup" in name or "web" in hints) and any(k in low for k in ("search", "look up", "find", "latest", "who is", "what is")):
                return {"tool_calls": [{"name": name, "arguments": {"query": text}}]}
            if ("save" in name or "write" in name or "file" in hints) and any(k in low for k in ("save", "write", "store")):
                return {"tool_calls": [{"name": name, "arguments": {"content": text}}]}
    if "flashcard" in low or "question" in low and "answer" in low:
        topic = (re.search(r"(?:about|on|for)\s+([a-zA-Z ]{3,40})", text) or [None, "the topic"])[1].strip()
        cards = [f"Q{i + 1}: What is {topic} fact {i + 1}? A{i + 1}: {topic.title()} fact {i + 1} explained simply." for i in range(5)]
        content = "\n".join(cards)
    elif "summar" in low:
        src = re.sub(r"(?is)^.*?summar\w*\s*(?:this|the following|the text|it)?\s*[:\-]?\s*", "", text).strip() or text
        first = re.split(r"(?<=[.!?])\s+", src.strip())[0][:160]
        content = f"Summary: {first.rstrip('.')} (summarised in one sentence)."
    elif "translate" in low:
        content = "Traducción simulada: " + text[-80:]
    elif "json" in low:
        content = json.dumps({"answer": "mock", "confidence": 0.5})
    else:
        content = f"Mock answer from neuromind-mock-1: {text[:120]}".rstrip()
    return {"content": content}


def handle(method: str, url: str, headers: dict | None = None, body: Any = None, params: dict | None = None) -> tuple[int, dict]:
    """Route one request. Returns (status, json_body). Raises nothing for client errors: they are JSON errors with a status."""
    method = method.upper()
    parts = urlsplit(url)
    if parts.netloc.lower() != HOST:
        return 502, {"error": "Internet access is disabled in the lab. Use https://api.neuromind.lab/v1/..."}
    q = {k: v[0] for k, v in parse_qs(parts.query).items()}
    q.update({k: str(v) for k, v in (params or {}).items()})
    h = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    path = parts.path.rstrip("/")
    if not path.startswith("/v1/"):
        return 404, {"error": "Unknown endpoint. All endpoints start with /v1/."}
    route = path[4:]
    try:
        data = _json_body(body) if method in ("POST", "PUT") else {}
    except MockHTTPError as e:
        return e.status, {"error": e.message}

    if route == "weather" and method == "GET":
        city = q.get("city", "").strip()
        if not city:
            return 400, {"error": "Missing query parameter: city"}
        if city.title() not in CITIES:
            return 404, {"error": f"Unknown city: {city}", "known_cities": CITIES}
        base = _h(city.title(), 1000)
        return 200, {"city": city.title(), "temperature_c": 18 + base % 17, "condition": CONDITIONS[base % len(CONDITIONS)], "humidity": 40 + base % 55, "unit": "celsius"}
    if route == "books" and method == "GET":
        rows = BOOKS
        if q.get("author"):
            rows = [b for b in rows if b["author"].lower() == q["author"].strip().lower()]
        if q.get("genre"):
            rows = [b for b in rows if b["genre"] == q["genre"].strip().lower()]
        return 200, {"count": len(rows), "books": rows}
    m = re.fullmatch(r"books/(\d+)", route)
    if m and method == "GET":
        book = next((b for b in BOOKS if b["id"] == int(m.group(1))), None)
        return (200, book) if book else (404, {"error": "Book not found"})
    if route == "news/headlines" and method == "GET":
        n = max(1, min(5, int(q.get("limit", "5") or 5)))
        return 200, {"headlines": HEADLINES[:n]}
    if route == "quotes/random" and method == "GET":
        _quote_counter[0] += 1
        return 200, QUOTES[(_quote_counter[0] - 1) % len(QUOTES)]
    if route == "secure/profile" and method == "GET":
        if "api_key" in q or "key" in q or "token" in q:
            return 401, {"error": "API keys must never be placed in the URL (it would be logged and exposed). Send 'Authorization: Bearer <key>' as a header."}
        auth = h.get("authorization", "")
        if auth == f"Bearer {TEST_KEY}":
            return 200, {"user": "student", "plan": "lab", "requests_left": 999}
        if not auth:
            return 401, {"error": "Missing Authorization header. Send 'Authorization: Bearer <key>'."}
        return 401, {"error": "Invalid API key."}
    if route == "flaky" and method == "GET":
        key = q.get("id", "default")
        _flaky_calls[key] = _flaky_calls.get(key, 0) + 1
        if _flaky_calls[key] % 3 != 0:
            return 503, {"error": "Service temporarily unavailable, please retry", "attempt": _flaky_calls[key]}
        return 200, {"ok": True, "attempt": _flaky_calls[key], "message": "Success after retrying"}
    if route == "search" and method == "GET":
        term = q.get("q", "").strip().lower()
        if not term:
            return 400, {"error": "Missing query parameter: q"}
        hits = next((v for k, v in SEARCH_RESULTS.items() if k in term), [])
        return 200, {"query": term, "results": hits or [{"title": f"About {term}", "url": f"https://example.org/{term.replace(' ', '-')}", "snippet": f"General information about {term}."}]}
    if route == "chat" and method == "POST":
        if h.get("authorization", "") not in ("", f"Bearer {TEST_KEY}"):
            return 401, {"error": "Invalid API key."}
        msgs = data.get("messages")
        if not isinstance(msgs, list) or not msgs or not all(isinstance(m, dict) and "role" in m and "content" in m for m in msgs):
            return 400, {"error": "Body must be {\"messages\": [{\"role\": ..., \"content\": ...}, ...]}"}
        reply = _chat_reply(msgs, data.get("tools"))
        prompt_tokens = sum(len(_words(str(m["content"]))) for m in msgs)
        message = {"role": "assistant", "content": reply.get("content", ""), **({"tool_calls": reply["tool_calls"]} if "tool_calls" in reply else {})}
        return 200, {"id": "chat-" + hashlib.sha256(json.dumps(msgs, sort_keys=True).encode()).hexdigest()[:12], "model": data.get("model") or "neuromind-mock-1",
                     "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if "tool_calls" in reply else "stop"}],
                     "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": len(_words(message["content"])), "total_tokens": prompt_tokens + len(_words(message["content"]))}}
    if route == "generate" and method == "POST":
        prompt = str(data.get("prompt", "")).strip()
        if not prompt:
            return 400, {"error": "Missing field: prompt"}
        n = max(1, min(5, int(data.get("n", 1) or 1)))
        outs = [f"Version {i + 1}: " + " ".join(w.capitalize() if (i + j) % 3 == 0 else w for j, w in enumerate(prompt.split()))[:200] + f" [seed {_h(prompt + str(i), 9000)}]" for i in range(n)]
        return 200, {"prompt": prompt, "outputs": outs, "model": "neuromind-gen-1"}
    if route == "sentiment" and method == "POST":
        text = str(data.get("text", ""))
        if not text.strip():
            return 400, {"error": "Missing field: text"}
        ws = _words(text)
        pos, neg = sum(w in POSITIVE for w in ws), sum(w in NEGATIVE for w in ws)
        if "not" in ws or "n't" in text.lower():
            pos, neg = neg, pos  # a crude negation flip; sarcasm is (deliberately) not understood
        label = "positive" if pos > neg else "negative" if neg > pos else "neutral"
        score = round(0.5 + 0.5 * abs(pos - neg) / max(1, pos + neg), 2) if pos != neg else 0.5
        return 200, {"label": label, "score": score, "positive_words": pos, "negative_words": neg}
    if route == "entities" and method == "POST":
        text = str(data.get("text", ""))
        found = []
        low = text.lower()
        for name in sorted(PEOPLE | PLACES | ORGS, key=len, reverse=True):
            if re.search(r"\b" + re.escape(name) + r"\b", low):
                kind = "PERSON" if name in PEOPLE else "PLACE" if name in PLACES else "ORG"
                found.append({"text": name.title() if kind != "ORG" else name.upper() if len(name) <= 4 else name.title(), "type": kind})
        return 200, {"entities": found}
    if route == "embeddings" and method == "POST":
        inp = data.get("input")
        items = [inp] if isinstance(inp, str) else inp
        if not isinstance(items, list) or not items or not all(isinstance(x, str) for x in items):
            return 400, {"error": "Body must be {\"input\": \"text\" or [\"text\", ...]}"}
        return 200, {"model": "neuromind-embed-64", "data": [{"index": i, "embedding": embed(x)} for i, x in enumerate(items[:64])]}
    if route in ("ocr", "vision/classify", "vision/detect", "vision/ask", "vision/caption") and method == "POST":
        name = str(data.get("image") or data.get("file") or data.get("image_name") or "")
        img = IMAGES.get(name.rsplit("/", 1)[-1])
        if not img:
            return 404, {"error": f"Unknown image '{name}'. Use one of the lab's image files: {sorted(IMAGES)}"}
        if route == "ocr":
            return 200, {"text": img["text"], "lines": [ln for ln in img["text"].split("\n") if ln]}
        if route == "vision/classify":
            return 200, {"labels": img["labels"]}
        if route == "vision/detect":
            return 200, {"objects": img["boxes"]}
        if route == "vision/caption":
            return 200, {"caption": img["caption"]}
        question = str(data.get("question", "")).lower()
        if not question:
            return 400, {"error": "Missing field: question"}
        if any(k in question for k in ("what", "describe", "see", "show")):
            answer = img["caption"]
        elif any(k in question for k in ("text", "say", "written", "read")):
            answer = img["text"] or "There is no readable text in this image."
        elif any(k in question for k in ("how many", "count")):
            answer = f"I can see {len(img['boxes']) or 1} main object(s)."
        else:
            answer = f"That question is not about the image; the image shows: {img['caption']}."
        return 200, {"answer": answer, "related_to_image": not answer.startswith("That question")}
    return 404, {"error": f"Unknown endpoint: {method} {path}"}


def call(method: str, path: str, **kwargs: Any) -> tuple[int, dict]:
    """Convenience for tests and helpers: call('GET', '/v1/weather', params={'city': 'Pune'})."""
    url = path if path.startswith("http") else BASE_URL.rsplit("/v1", 1)[0] + path
    return handle(method, url, kwargs.get("headers"), kwargs.get("json") if "json" in kwargs else kwargs.get("data"), kwargs.get("params"))


# ---------------------------------------------------------------- requests integration
_installed = False


def install() -> bool:
    """Mount the simulator on every requests.Session (returns False when requests is not importable)."""
    global _installed
    if _installed:
        return True
    try:
        import requests
        from requests.adapters import BaseAdapter
    except Exception:  # noqa: BLE001
        return False

    class LabAdapter(BaseAdapter):
        def send(self, request, **kwargs):  # noqa: ANN001
            status, payload = handle(request.method, request.url, dict(request.headers), request.body)
            resp = requests.Response()
            resp.status_code = status
            resp.reason = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 404: "Not Found", 502: "Bad Gateway", 503: "Service Unavailable"}.get(status, "")
            resp._content = json.dumps(payload).encode("utf-8")  # noqa: SLF001
            resp.headers["Content-Type"] = "application/json"
            resp.headers["X-NeuroMind-Mock"] = VERSION
            resp.url = request.url
            resp.request = request
            resp.encoding = "utf-8"
            return resp

        def close(self):  # noqa: ANN001
            return None

    class BlockedAdapter(BaseAdapter):
        def send(self, request, **kwargs):  # noqa: ANN001
            raise requests.ConnectionError(f"Internet access is disabled in the lab: {request.url}. Use {BASE_URL}/...")

        def close(self):  # noqa: ANN001
            return None

    original_init = requests.Session.__init__

    def patched_init(self, *a, **kw):  # noqa: ANN001
        original_init(self, *a, **kw)
        self.mount("https://", BlockedAdapter())
        self.mount("http://", BlockedAdapter())
        self.mount(f"https://{HOST}", LabAdapter())
        self.mount(f"http://{HOST}", LabAdapter())

    requests.Session.__init__ = patched_init  # type: ignore[method-assign]
    _installed = True
    return True
