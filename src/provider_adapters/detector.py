from __future__ import annotations

from urllib.parse import urlparse


def detect_provider(url: str) -> str:
    normalized_url = _normalize_url(url)
    hostname = urlparse(normalized_url).hostname or ""
    hostname = hostname.lower()

    if hostname.endswith("leetcode.com"):
        return "leetcode"
    if hostname.endswith("programmers.co.kr"):
        return "programmers"
    if hostname.endswith("acmicpc.net"):
        return "baekjoon"
    if hostname.endswith("codeforces.com"):
        return "codeforces"
    if hostname.endswith("atcoder.jp"):
        return "atcoder"
    return ""


def _normalize_url(url: str) -> str:
    value = str(url or "").strip()
    if "://" not in value and "." in value:
        return f"https://{value}"
    return value
