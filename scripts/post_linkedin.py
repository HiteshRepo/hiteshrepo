import json
import os
import sys
import xml.etree.ElementTree as ET

import anthropic
import requests
from openai import OpenAI

BLOG_RSS = "https://hiteshpattanayak.info/posts/index.xml"
GITHUB_USERNAME = "hiteshrepo"
MAX_POSTS = 3
MAX_COMMITS = 10

LINKEDIN_API_URL = "https://api.linkedin.com/v2/ugcPosts"


def fetch_recent_posts() -> list[dict]:
    try:
        response = requests.get(BLOG_RSS, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        posts = []
        for item in root.findall(".//item")[:MAX_POSTS]:
            title = item.find("title")
            link = item.find("link")
            if title is not None and link is not None:
                posts.append({"title": title.text, "link": link.text})
        return posts
    except Exception as e:
        print(f"Warning: could not fetch RSS feed: {e}", file=sys.stderr)
        return []


def fetch_recent_commits() -> list[str]:
    try:
        token = os.environ.get("GITHUB_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = requests.get(
            f"https://api.github.com/users/{GITHUB_USERNAME}/events",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        events = response.json()
        commits = []
        for event in events:
            if event.get("type") != "PushEvent":
                continue
            repo = event.get("repo", {}).get("name", "")
            for commit in event.get("payload", {}).get("commits", []):
                message = commit.get("message", "").splitlines()[0]
                if message.startswith("chore: auto-update"):
                    continue
                commits.append(f"{repo}: {message}")
            if len(commits) >= MAX_COMMITS:
                break
        return commits[:MAX_COMMITS]
    except Exception as e:
        print(f"Warning: could not fetch GitHub commits: {e}", file=sys.stderr)
        return []


PROMPT_SYSTEM = (
    "You are Hitesh Pattanayak, a Senior Software Engineer working on "
    "data pipelines, AI/LLM tools, Kubernetes, and cloud-native systems. "
    "You write concise, thoughtful LinkedIn posts that feel authentic, not promotional."
)

PROMPT_INSTRUCTION = (
    "Write a short LinkedIn post (3-5 sentences) in first person about what you are "
    "currently working on or thinking about technically. Be specific and concrete. "
    "End with 3-5 relevant hashtags on a new line. "
    "No fluff, no 'Excited to share' or 'Thrilled to announce' opener phrases."
)


def build_user_message(posts: list[dict], commits: list[str]) -> str:
    parts = []
    if posts:
        post_lines = "\n".join(f"- {p['title']} ({p['link']})" for p in posts)
        parts.append(f"Recent blog posts:\n{post_lines}")
    if commits:
        parts.append("Recent GitHub commits:\n" + "\n".join(f"- {c}" for c in commits))
    if not parts:
        parts.append(
            "Tech focus: data pipelines, Kubernetes, gRPC, AI/LLM tooling, "
            "Go, Python, Azure, Databricks, RAG, OpenAI and Anthropic APIs."
        )
    return "\n\n".join(parts) + f"\n\n{PROMPT_INSTRUCTION}"


def generate_with_openai(user_message: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
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
        max_tokens=300,
        system=PROMPT_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text.strip()


def generate_post(posts: list[dict], commits: list[str]) -> str:
    user_message = build_user_message(posts, commits)

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


def post_to_linkedin(text: str) -> None:
    access_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    person_id = os.environ["LINKEDIN_PERSON_ID"]

    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }

    response = requests.post(
        LINKEDIN_API_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        data=json.dumps(payload),
        timeout=10,
    )
    response.raise_for_status()
    print(f"Posted to LinkedIn. Status: {response.status_code}")


if __name__ == "__main__":
    posts = fetch_recent_posts()
    print(f"Fetched {len(posts)} recent posts.")
    commits = fetch_recent_commits()
    print(f"Fetched {len(commits)} recent commits.")
    post_text = generate_post(posts, commits)
    print(f"Generated post:\n{post_text}")
    post_to_linkedin(post_text)
