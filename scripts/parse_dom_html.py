#!/usr/bin/env python3

"""
parse_dom_html.py

Parses client-exported Claude DOM HTML files (e.g. from Chrome or Electron "Save Page As")
to recover rendered conversation bubbles, markdown outputs, and timestamps.

Usage:
  python3 parse_dom_html.py <file.html> [--out <output.md>]
"""

import sys
import os
import re
import argparse
from html.parser import HTMLParser


class ClaudeDOMParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_blocks = []
        self.current_block = []
        self.ignore_tags = {"script", "style", "svg", "path", "head"}
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        if tag.lower() in ["p", "div", "h1", "h2", "h3", "li"]:
            if self.current_block:
                text = " ".join(self.current_block).strip()
                if text:
                    self.text_blocks.append(text)
                self.current_block = []

    def handle_endtag(self, tag):
        if self.current_block:
            text = " ".join(self.current_block).strip()
            if text:
                self.text_blocks.append(text)
            self.current_block = []
        self.current_tag = None

    def handle_data(self, data):
        if self.current_tag in self.ignore_tags:
            return
        cleaned = data.strip()
        if cleaned:
            self.current_block.append(cleaned)


def main():
    parser = argparse.ArgumentParser(description="Parse Claude DOM HTML export.")
    parser.add_argument("html_file", help="Path to exported HTML file")
    parser.add_argument("--out", "-o", help="Output markdown file path")
    args = parser.parse_args()

    with open(args.html_file, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()

    p = ClaudeDOMParser()
    p.feed(html_content)

    print(f"[INFO] Parsed {len(p.text_blocks)} structural text blocks from {args.html_file}...")

    # Filter out UI noise (CSS, buttons, labels)
    filtered = []
    for b in p.text_blocks:
        if len(b) < 3:
            continue
        if b.startswith("html.") or b.startswith("@keyframes") or b.startswith(".ucoub-enter"):
            continue
        filtered.append(b)

    output_text = "# Exported Claude DOM Snapshot\n\n" + "\n\n".join(filtered)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as out_f:
            out_f.write(output_text)
        print(f"[SUCCESS] Saved extracted text to: {args.out}")
    else:
        print(output_text[:2000])


if __name__ == "__main__":
    main()
