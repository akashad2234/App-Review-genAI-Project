import json
from pathlib import Path
from typing import Any, Dict, List

from src.llm.gemini_client import GeminiClient


REVIEWS_PATH = Path("data/reports/reviews/reviews.json")
THEMES_PATH = Path("data/reports/themes/themes.json")


def load_filtered_reviews() -> List[Dict[str, Any]]:
    with REVIEWS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    reviews = data.get("reviews", [])
    if not isinstance(reviews, list):
        raise ValueError("reviews field must be a list")
    return reviews


def load_themes() -> List[Dict[str, Any]]:
    if not THEMES_PATH.exists():
        return []
    with THEMES_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    themes = data.get("themes", [])
    if not isinstance(themes, list):
        raise ValueError("themes field must be a list")
    return themes


def build_theme_prompt(sample_texts: List[str], n_themes: int = 5) -> List[Dict[str, str]]:
    joined_reviews = "\n\n".join(sample_texts)
    system = (
        "You are an expert product analyst for the Groww investing app. "
        "You analyze Play Store reviews and identify key product and experience themes."
    )
    user = f"""
Given the following Groww app Play Store reviews, identify exactly {n_themes} distinct themes
that best summarize what users are talking about.

Output one line per theme. Each line must use this exact format (with a pipe character between fields):
ThemeName | sentiment | One sentence description.

Rules:
- ThemeName: short label, max 5 words. Do not use pipe (|) inside the name.
- sentiment: exactly one of: positive, negative, mixed
- One sentence description: one sentence; avoid using pipe (|) inside it.

Output only these {n_themes} lines, no numbering, no JSON, no other text.

Reviews:
{joined_reviews}
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_theme_lines(text: str) -> List[Dict[str, Any]]:
    """Parse line-based theme output into list of {name, description, sentiment}."""
    themes: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(" | ", 2)
        if len(parts) < 3:
            continue
        name = parts[0].strip()
        sentiment = parts[1].strip().lower()
        description = parts[2].strip()
        if name and description:
            if sentiment not in ("positive", "negative", "mixed"):
                sentiment = "mixed"
            themes.append({"name": name, "description": description, "sentiment": sentiment})
    return themes


def build_grouping_prompt(
    themes: List[Dict[str, Any]], reviews: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    system = (
        "You are an expert product analyst. "
        "You assign each app review to exactly one of a small set of themes."
    )
    theme_names = [t.get("name", "") for t in themes if t.get("name")]
    themes_list = "\n".join(f"- {n}" for n in theme_names)
    reviews_minimal = [
        {"reviewId": r.get("reviewId"), "text": r.get("text", "")} for r in reviews
    ]
    reviews_json = json.dumps(reviews_minimal, ensure_ascii=False, indent=2)
    user = f"""
We have the following themes (use the exact name when assigning):

{themes_list}

Assign each of the following reviews to exactly one theme. Output one line per review in this exact format:
reviewId -> ThemeName

Use the reviewId exactly as in the list. Use the theme name exactly as in the list above. No JSON, no other text.

Reviews:
{reviews_json}
""".strip()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_grouping_lines(text: str, valid_review_ids: set) -> Dict[str, str]:
    """Parse line-based grouping output into reviewId -> themeName."""
    review_to_theme: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or " -> " not in line:
            continue
        left, _, right = line.partition(" -> ")
        rid = left.strip()
        tname = right.strip()
        if rid in valid_review_ids and tname:
            review_to_theme[rid] = tname
    return review_to_theme


def run() -> Dict[str, Any]:
    reviews = load_filtered_reviews()
    if not reviews:
        raise ValueError("No filtered reviews available. Run Phase 1 + Phase 2 first.")

    # Use all available filtered reviews (current volume is manageable)
    sample_texts = [str(r.get("text", "")).strip() for r in reviews if r.get("text")]

    client = GeminiClient()
    messages = build_theme_prompt(sample_texts, n_themes=5)

    system_inst = messages[0]["content"]
    user_prompt = messages[1]["content"]

    result_text = client.generate_json(system_inst, user_prompt)

    themes = parse_theme_lines(result_text)
    if not themes:
        raise ValueError(
            "No themes parsed from model output. Expected line-based format: ThemeName | sentiment | description"
        )

    # Second step: assign each review to a theme
    grouping_messages = build_grouping_prompt(themes, reviews)
    grouping_system = grouping_messages[0]["content"]
    grouping_user = grouping_messages[1]["content"]
    grouping_text = client.generate_json(grouping_system, grouping_user)

    valid_review_ids = {str(r.get("reviewId", "")).strip() for r in reviews}
    review_to_theme = parse_grouping_lines(grouping_text, valid_review_ids)

    # Organize reviews under themes
    themes_by_name: Dict[str, Dict[str, Any]] = {t["name"]: t for t in themes}
    grouped: Dict[str, List[Dict[str, Any]]] = {t["name"]: [] for t in themes}
    for r in reviews:
        rid = str(r.get("reviewId", "")).strip()
        tname = review_to_theme.get(rid)
        if tname in grouped:
            grouped[tname].append(r)

    # Write combined structure to file
    THEMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with THEMES_PATH.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "source": str(REVIEWS_PATH),
                "total_reviews": len(reviews),
                "sampled_reviews": len(sample_texts),
                "themes": [
                    {
                        **themes_by_name[name],
                        "reviews": grouped.get(name, []),
                    }
                    for name in themes_by_name
                ],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return {
        "themes": [
            {**themes_by_name[name], "review_count": len(grouped.get(name, []))}
            for name in themes_by_name
        ],
        "total_reviews": len(reviews),
    }


if __name__ == "__main__":
    run()

