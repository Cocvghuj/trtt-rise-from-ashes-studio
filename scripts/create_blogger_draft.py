#!/usr/bin/env python3
"""Validate the Rise From Ashes article and create one verified Blogger DRAFT.

This script never publishes, updates, deletes, or replaces an existing post.
"""
from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ARTICLE = Path("blogger-drafts/rise-from-ashes.html")
MARKER = "TRTT_VOYAGE_RISE_FROM_ASHES_787950"
REQUIRED_URL = "https://trttvoyage.com"
LABELS = ["TRTT Voyage", "Personal Reflection", "Rise From Ashes", "787950"]


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.text_parts: list[str] = []
        self.h1_count = 0
        self.h2_count = 0
        self.h3_count = 0
        self.links: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag)
        attrs_dict = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        elif tag == "h2":
            self.h2_count += 1
        elif tag == "h3":
            self.h3_count += 1
        if tag == "a":
            self.links.append(attrs_dict.get("href", ""))
        if tag in {"script", "iframe", "form", "object", "embed"}:
            self.errors.append(f"Disallowed element: {tag}")
        for name, value in attrs:
            if name.lower().startswith("on"):
                self.errors.append(f"Disallowed event attribute: {name}")
            if name.lower() in {"src", "srcdoc"}:
                self.errors.append(f"External/embedded resource attribute not allowed: {name}")
            if name.lower() == "href" and value and value.strip().lower().startswith(
                ("javascript:", "data:")
            ):
                self.errors.append("Unsafe link scheme detected")

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)


def validate_article() -> tuple[str, str]:
    if not ARTICLE.is_file():
        raise RuntimeError(f"Article file not found: {ARTICLE}")
    content = ARTICLE.read_text(encoding="utf-8")
    if MARKER not in content:
        raise RuntimeError("Unique TRTT article marker is missing.")
    if REQUIRED_URL not in content:
        raise RuntimeError("Required TRTT Voyage website link is missing.")
    if "<!--" not in content or "-->" not in content:
        raise RuntimeError("Article marker comment is malformed.")
    if re.search(r"<!doctype|<html\b|<head\b|<body\b", content, re.I):
        raise RuntimeError("Provide Blogger post-body HTML only, not a full document.")
    parser = ArticleParser()
    parser.feed(content)
    parser.close()
    text = " ".join(parser.text_parts)
    words = re.findall(r"\b[\w’'-]+\b", text)
    if parser.errors:
        raise RuntimeError("; ".join(parser.errors))
    if parser.h1_count != 1:
        raise RuntimeError(f"Expected exactly one H1; found {parser.h1_count}.")
    if parser.h2_count < 5:
        raise RuntimeError(f"Article needs at least five H2 sections; found {parser.h2_count}.")
    if parser.h3_count < 3:
        raise RuntimeError("FAQ section is incomplete; at least three H3 questions are required.")
    if len(words) < 400:
        raise RuntimeError(f"Article is too short ({len(words)} words); minimum is 400.")
    if not any(url == REQUIRED_URL for url in parser.links):
        raise RuntimeError("TRTT website link must be a real anchor.")
    if "Disclosure:" not in text:
        raise RuntimeError("Disclosure is missing.")
    if re.search(r"\b(published|live)\b", text, re.I) and "not a news report" not in text.lower():
        raise RuntimeError("Disclosure check failed.")
    title_match = re.search(r"<h1\b[^>]*>(.*?)</h1>", content, re.I | re.S)
    if not title_match:
        raise RuntimeError("Title could not be extracted.")
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
    if not title or len(title) > 100:
        raise RuntimeError("Title is empty or longer than 100 characters.")
    return title, content


def create_or_verify_draft(title: str, content: str) -> None:
    required = (
        "BLOGGER_BLOG_ID",
        "BLOGGER_CLIENT_ID",
        "BLOGGER_CLIENT_SECRET",
        "BLOGGER_REFRESH_TOKEN",
    )
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError("Missing required GitHub Actions secret(s): " + ", ".join(missing))

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    blog_id = os.environ["BLOGGER_BLOG_ID"].strip()
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["BLOGGER_CLIENT_ID"],
        client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/blogger"],
    )
    api = build("blogger", "v3", credentials=credentials, cache_discovery=False)

    # Search both draft and live posts before creating anything. Never overwrite.
    token = None
    matches = []
    while True:
        params = {
            "blogId": blog_id,
            "fetchBodies": True,
            "maxResults": 500,
            "status": ["DRAFT", "LIVE"],
            "view": "ADMIN",
        }
        if token:
            params["pageToken"] = token
        page = api.posts().list(**params).execute(num_retries=5)
        for post in page.get("items", []):
            post_title = (post.get("title") or "").strip().casefold()
            post_content = post.get("content") or ""
            if MARKER in post_content or post_title == title.casefold():
                matches.append(post)
        token = page.get("nextPageToken")
        if not token:
            break

    if matches:
        # Any LIVE collision blocks the run, even if a separate matching draft exists.
        if any((post.get("status") or "").upper() == "LIVE" for post in matches):
            raise RuntimeError("A matching LIVE post exists; refusing to create or modify a duplicate.")
        marked = [post for post in matches if MARKER in (post.get("content") or "")]
        if (
            len(matches) == 1
            and len(marked) == 1
            and (marked[0].get("status") or "").upper() == "DRAFT"
        ):
            print(
                "PASS: Existing matching Blogger DRAFT verified; "
                f"post_id={marked[0].get('id')}; no duplicate created."
            )
            return
        raise RuntimeError(
            "A matching title/marker already exists but cannot be safely verified as one DRAFT; "
            "manual review required. No post was changed."
        )

    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": LABELS,
    }
    created = api.posts().insert(
        blogId=blog_id,
        body=body,
        isDraft=True,
    ).execute(num_retries=5)
    post_id = str(created.get("id") or "").strip()
    if not post_id:
        raise RuntimeError("Blogger returned no post ID; refusing to report success.")

    verified = api.posts().get(
        blogId=blog_id,
        postId=post_id,
        view="ADMIN",
    ).execute(num_retries=5)
    status = (verified.get("status") or "").upper()
    if status != "DRAFT":
        raise RuntimeError(
            f"Post {post_id} was created but verification returned status={status or 'UNKNOWN'}; "
            "manual review required. It was not intentionally published."
        )
    if MARKER not in (verified.get("content") or ""):
        raise RuntimeError(
            f"Post {post_id} status is DRAFT but article marker readback failed."
        )
    print(f"PASS: Blogger DRAFT created and read back; post_id={post_id}; status=DRAFT.")


def main() -> int:
    try:
        title, content = validate_article()
        word_count = len(re.findall(r"\b[\w’'-]+\b", re.sub(r"<[^>]+>", " ", content)))
        print(f"PASS: Article validation; title={title!r}; approximately {word_count} words.")
        if "--validate-only" in sys.argv:
            return 0
        create_or_verify_draft(title, content)
        print("PASS: Draft workflow complete. No live publication or Telegram message was sent.")
        return 0
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
