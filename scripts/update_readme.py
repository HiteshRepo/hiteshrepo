import os
import re
import sys
import xml.etree.ElementTree as ET

import anthropic
import requests
from openai import OpenAI

BLOG_RSS = "https://hitesh-pattanayak.netlify.app/index.xml"
README_PATH = "README.md"
MARKER_START = "<!-- THINKING_START -->"
MARKER_END = "<!-- THINKING_END -->"
MAX_POSTS = 5


def fetch_recent_posts() -> list[str]:
    try:
        response = requests.get(BLOG_RSS, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        titles = [
            item.find("title").text
            for item in root.findall(".//item")[:MAX_POSTS]
            if item.find("title") is not None
        ]
        return titles
    except Exception as e:
        print(f"Warning: could not fetch RSS feed: {e}", file=sys.stderr)
        return []


PROMPT_SYSTEM = (
    "You are Hitesh Pattanayak, a Senior Software Engineer working on "
    "data pipelines, AI/LLM tools, Kubernetes, and cloud-native systems."
)

PROMPT_INSTRUCTION = (
    "Write a single short paragraph (2-3 sentences) in first person about "
    "what you are currently thinking about or exploring technically. "
    "Be specific and concrete. No fluff, no intro phrases like 'Currently I am'."
)


def build_user_message(posts: list[str]) -> str:
    if posts:
        context = "Recent blog posts:\n" + "\n".join(f"- {p}" for p in posts)
    else:
        context = (
            "Tech focus: data pipelines, Kubernetes, gRPC, AI/LLM tooling, "
            "Go, Python, Azure, Databricks, RAG, OpenAI and Anthropic APIs."
        )
    return f"{context}\n\n{PROMPT_INSTRUCTION}"


def generate_with_openai(user_message: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=150,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_with_anthropic(user_message: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        system=PROMPT_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text.strip()


def generate_thinking(posts: list[str]) -> str:
    user_message = build_user_message(posts)

    if os.environ.get("OPENAI_API_KEY"):
        try:
            print("Generating with OpenAI...")
            return generate_with_openai(user_message)
        except Exception as e:
            print(f"Warning: OpenAI failed: {e}", file=sys.stderr)

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            print("Falling back to Anthropic...")
            return generate_with_anthropic(user_message)
        except Exception as e:
            print(f"Warning: Anthropic failed: {e}", file=sys.stderr)

    print("Error: no API key available or both providers failed.", file=sys.stderr)
    sys.exit(1)


def update_readme(thinking: str) -> None:
    with open(README_PATH, "r") as f:
        readme = f.read()

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL,
    )

    if not pattern.search(readme):
        print("Error: markers not found in README.md", file=sys.stderr)
        sys.exit(1)

    replacement = f"{MARKER_START}\n{thinking}\n{MARKER_END}"
    updated = pattern.sub(replacement, readme)

    with open(README_PATH, "w") as f:
        f.write(updated)

    print("README.md updated successfully.")


if __name__ == "__main__":
    posts = fetch_recent_posts()
    print(f"Fetched {len(posts)} recent posts.")
    thinking = generate_thinking(posts)
    print(f"Generated blurb:\n{thinking}")
    update_readme(thinking)
