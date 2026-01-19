#!/usr/bin/env python3
"""
Migrate LESSONS-LEARNED.md and LESSONS-SCRATCH.md to LCIS database.
"""

import re
import httpx
import asyncio
from pathlib import Path

LIBRARIAN_URL = "http://localhost:8050"
LESSONS_LEARNED = Path("/opt/leveredge/LESSONS-LEARNED.md")
LESSONS_SCRATCH = Path("/opt/leveredge/LESSONS-SCRATCH.md")

# Domain mapping from content keywords
DOMAIN_KEYWORDS = {
    "THE_KEEP": ["docker", "container", "backup", "server", "infrastructure", "caddy", "nginx", "systemctl", "service", "chronos", "hades"],
    "SENTINELS": ["security", "auth", "credential", "permission", "ssl", "certificate", "aegis", "password"],
    "CHANCERY": ["business", "client", "project", "planning", "strategy", "consul", "varys"],
    "ARIA_SANCTUM": ["aria", "prompt", "personality", "chat", "assistant"],
    "ALCHEMY": ["content", "creative", "writing", "design", "muse", "quill"],
}

# Type inference patterns
FAILURE_PATTERNS = ["don't", "never", "avoid", "failed", "error", "broken", "wrong", "issue", "problem", "doesn't work", "not work"]
SUCCESS_PATTERNS = ["worked", "success", "solution", "fixed", "works", "correct", "use this"]
WARNING_PATTERNS = ["warning", "careful", "watch out", "be aware", "note:", "important:"]


def infer_domain(content: str) -> str:
    content_lower = content.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            return domain
    return "THE_KEEP"  # Default


def infer_type(content: str) -> str:
    content_lower = content.lower()
    if any(w in content_lower for w in FAILURE_PATTERNS):
        return "failure"
    if any(w in content_lower for w in SUCCESS_PATTERNS):
        return "success"
    if any(w in content_lower for w in WARNING_PATTERNS):
        return "warning"
    return "insight"


def infer_severity(content: str, lesson_type: str) -> str:
    content_lower = content.lower()
    if lesson_type != "failure":
        return "medium"

    # Critical indicators
    if any(w in content_lower for w in ["data loss", "production", "corrupt", "broken", "critical"]):
        return "critical"
    # High severity
    if any(w in content_lower for w in ["restart", "rebuild", "hours", "major"]):
        return "high"
    return "medium"


def extract_tags(content: str) -> list:
    """Extract relevant tags from content"""
    tags = []
    content_lower = content.lower()

    tag_keywords = {
        "docker": ["docker", "container", "image", "compose"],
        "n8n": ["n8n", "workflow", "node"],
        "supabase": ["supabase", "postgres", "database"],
        "aria": ["aria", "chat", "assistant"],
        "git": ["git", "commit", "push", "pull"],
        "api": ["api", "endpoint", "rest", "http"],
        "prompt": ["prompt", "system prompt", "personality"],
        "backup": ["backup", "restore", "chronos", "hades"],
        "credential": ["credential", "secret", "key", "token", "password"],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in content_lower for kw in keywords):
            tags.append(tag)

    return tags[:5]  # Limit to 5 tags


def parse_lessons_markdown(content: str) -> list:
    """Parse markdown into individual lessons"""
    lessons = []

    # Split by headers or bullet points
    lines = content.split('\n')
    current_lesson = []
    current_section = "general"

    for line in lines:
        # Check for section header
        if line.startswith('##'):
            current_section = line.strip('# ').lower()
            continue

        # Skip empty lines and horizontal rules
        if not line.strip() or line.strip().startswith('---'):
            if current_lesson:
                lessons.append({
                    "content": ' '.join(current_lesson),
                    "section": current_section
                })
                current_lesson = []
            continue

        # Check for bullet point (lesson start)
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            if current_lesson:
                lessons.append({
                    "content": ' '.join(current_lesson),
                    "section": current_section
                })
            current_lesson = [line.strip('- *').strip()]
        elif line.strip() and current_lesson:
            # Continuation of current lesson
            current_lesson.append(line.strip())
        elif line.strip().startswith('#'):
            # New section header
            if current_lesson:
                lessons.append({
                    "content": ' '.join(current_lesson),
                    "section": current_section
                })
                current_lesson = []
            current_section = line.strip('# ').lower()

    # Don't forget last lesson
    if current_lesson:
        lessons.append({
            "content": ' '.join(current_lesson),
            "section": current_section
        })

    # Filter out empty or too-short lessons
    return [l for l in lessons if len(l["content"]) >= 20]


async def migrate_lesson(lesson: dict, source_file: str) -> dict:
    """Send lesson to LCIS Librarian"""
    content = lesson["content"]
    lesson_type = infer_type(content)

    # Extract title from first sentence or first 100 chars
    title = content.split('.')[0][:100] if '.' in content else content[:100]

    payload = {
        "content": content,
        "title": title,
        "type": lesson_type,
        "domain": infer_domain(content),
        "severity": infer_severity(content, lesson_type),
        "tags": extract_tags(content) + [lesson["section"]],
        "source_agent": "MIGRATION",
        "source_type": "migration",
        "source_context": {"file": source_file, "section": lesson["section"]}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LIBRARIAN_URL}/ingest",
            json=payload,
            timeout=30.0
        )
        return response.json()


async def main():
    print("=" * 60)
    print("LCIS Migration: LESSONS-LEARNED.md -> Database")
    print("=" * 60)

    # Check if LIBRARIAN is available
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{LIBRARIAN_URL}/health", timeout=5.0)
            if resp.status_code != 200:
                print(f"ERROR: LIBRARIAN not healthy: {resp.text}")
                return
            print(f"LIBRARIAN: {resp.json()}")
    except Exception as e:
        print(f"ERROR: Cannot connect to LIBRARIAN at {LIBRARIAN_URL}")
        print(f"       Make sure LCIS services are running: {e}")
        return

    total_success = 0
    total_failed = 0
    total_duplicates = 0

    # Migrate LESSONS-LEARNED.md
    if LESSONS_LEARNED.exists():
        print(f"\nProcessing: {LESSONS_LEARNED}")
        content = LESSONS_LEARNED.read_text()
        lessons = parse_lessons_markdown(content)
        print(f"  Found {len(lessons)} lessons")

        for i, lesson in enumerate(lessons, 1):
            try:
                result = await migrate_lesson(lesson, "LESSONS-LEARNED.md")
                if result.get("duplicate"):
                    total_duplicates += 1
                    print(f"  [{i}] DUPLICATE: {lesson['content'][:50]}...")
                else:
                    total_success += 1
                    print(f"  [{i}] OK: {lesson['content'][:50]}...")
            except Exception as e:
                total_failed += 1
                print(f"  [{i}] FAILED: {e}")
    else:
        print(f"File not found: {LESSONS_LEARNED}")

    # Migrate LESSONS-SCRATCH.md
    if LESSONS_SCRATCH.exists():
        print(f"\nProcessing: {LESSONS_SCRATCH}")
        content = LESSONS_SCRATCH.read_text()
        lessons = parse_lessons_markdown(content)
        print(f"  Found {len(lessons)} lessons")

        for i, lesson in enumerate(lessons, 1):
            try:
                result = await migrate_lesson(lesson, "LESSONS-SCRATCH.md")
                if result.get("duplicate"):
                    total_duplicates += 1
                    print(f"  [{i}] DUPLICATE: {lesson['content'][:50]}...")
                else:
                    total_success += 1
                    print(f"  [{i}] OK: {lesson['content'][:50]}...")
            except Exception as e:
                total_failed += 1
                print(f"  [{i}] FAILED: {e}")
    else:
        print(f"File not found: {LESSONS_SCRATCH}")

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"  Migrated:   {total_success}")
    print(f"  Duplicates: {total_duplicates}")
    print(f"  Failed:     {total_failed}")

    # Get dashboard stats
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{LIBRARIAN_URL}/dashboard", timeout=5.0)
            if resp.status_code == 200:
                dashboard = resp.json()
                print(f"\nLCIS Dashboard:")
                print(f"  Total lessons: {dashboard.get('total_lessons', 0)}")
                print(f"  Failures:      {dashboard.get('failures', 0)}")
                print(f"  Successes:     {dashboard.get('successes', 0)}")
                print(f"  Active rules:  {dashboard.get('active_rules', 0)}")
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())
