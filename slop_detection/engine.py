import json
import math
import os
import re
from collections import Counter
from statistics import mean, pvariance

import requests


_FILLER_PHRASES = [
    "at the end of the day",
    "in conclusion",
    "it goes without saying",
    "needless to say",
    "as we all know",
    "in today's world",
    "moving forward",
    "in the grand scheme",
    "the fact of the matter",
    "basically",
    "very",
    "really",
    "kind of",
    "sort of",
    "pretty much",
    "in some sense",
    "for all intents and purposes",
    "the reality is",
    "at its core",
    "on the other hand",
    "in general",
]

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "because",
    "as",
    "of",
    "at",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "from",
    "up",
    "down",
    "in",
    "out",
    "on",
    "off",
    "over",
    "under",
    "again",
    "further",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "can",
    "will",
    "just",
}

_POSITIVE_WORDS = {
    "good",
    "great",
    "excellent",
    "positive",
    "beneficial",
    "successful",
    "improve",
    "improves",
    "improved",
    "strong",
    "clear",
    "effective",
    "efficient",
}

_NEGATIVE_WORDS = {
    "bad",
    "poor",
    "negative",
    "weak",
    "unclear",
    "ineffective",
    "inefficient",
    "problem",
    "problems",
    "risk",
    "risks",
    "fail",
    "fails",
    "failed",
}


def _normalize_text(text):
    return re.sub(r"\s+", " ", text.strip())


def _split_paragraphs(text):
    chunks = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return chunks


def _split_sentences(text):
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw if s.strip()]


def _tokenize(text):
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    return [t for t in tokens if t and t not in _STOPWORDS and len(t) > 2]


def _claim_candidates(sentences):
    claim_markers = (
        "is",
        "are",
        "will",
        "must",
        "always",
        "never",
        "proves",
        "shows",
        "demonstrates",
        "guarantees",
    )
    candidates = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(marker in lowered for marker in claim_markers):
            candidates.append(sentence)
    return candidates


def _filler_density(text):
    lowered = text.lower()
    filler_hits = 0
    for phrase in _FILLER_PHRASES:
        filler_hits += lowered.count(phrase)
    word_count = max(len(re.findall(r"\w+", lowered)), 1)
    return min(1.0, filler_hits / word_count)


def _repetition_score(sentences):
    normalized = [re.sub(r"\W+", " ", s.lower()).strip() for s in sentences]
    normalized = [s for s in normalized if s]
    if not normalized:
        return 0.0
    duplicates = len(normalized) - len(set(normalized))
    return duplicates / len(normalized)


def _paragraph_sentiment(paragraphs):
    scores = []
    for paragraph in paragraphs:
        tokens = _tokenize(paragraph)
        pos = sum(1 for t in tokens if t in _POSITIVE_WORDS)
        neg = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
        if pos == 0 and neg == 0:
            scores.append(0.0)
        else:
            scores.append((pos - neg) / (pos + neg))
    return scores


def _topic_clusters(paragraphs, similarity_threshold=0.35, max_keywords=6):
    vectors = []
    vocab = set()
    for paragraph in paragraphs:
        tokens = _tokenize(paragraph)
        counts = Counter(tokens)
        vectors.append(counts)
        vocab.update(counts)

    def cosine(a, b):
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        numerator = sum(a[t] * b[t] for t in common)
        denom_a = math.sqrt(sum(v * v for v in a.values()))
        denom_b = math.sqrt(sum(v * v for v in b.values()))
        if denom_a == 0 or denom_b == 0:
            return 0.0
        return numerator / (denom_a * denom_b)

    clusters = []
    for idx, vector in enumerate(vectors):
        assigned = False
        for cluster in clusters:
            if cosine(vector, cluster["centroid"]) >= similarity_threshold:
                cluster["paragraph_indices"].append(idx)
                for token, count in vector.items():
                    cluster["centroid"][token] = cluster["centroid"].get(token, 0) + count
                assigned = True
                break
        if not assigned:
            clusters.append({
                "paragraph_indices": [idx],
                "centroid": dict(vector),
            })

    result = []
    for idx, cluster in enumerate(clusters):
        keywords = [token for token, _ in Counter(cluster["centroid"]).most_common(max_keywords)]
        result.append({
            "cluster_id": idx,
            "paragraph_indices": cluster["paragraph_indices"],
            "keywords": keywords,
        })
    return result


def _topic_drift(paragraphs, similarity_threshold=0.2):
    if len(paragraphs) < 2:
        return []
    vectors = []
    for paragraph in paragraphs:
        vectors.append(Counter(_tokenize(paragraph)))

    def cosine(a, b):
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        numerator = sum(a[t] * b[t] for t in common)
        denom_a = math.sqrt(sum(v * v for v in a.values()))
        denom_b = math.sqrt(sum(v * v for v in b.values()))
        if denom_a == 0 or denom_b == 0:
            return 0.0
        return numerator / (denom_a * denom_b)

    drift_points = []
    for idx in range(1, len(vectors)):
        similarity = cosine(vectors[idx - 1], vectors[idx])
        if similarity < similarity_threshold:
            drift_points.append({
                "from_paragraph": idx - 1,
                "to_paragraph": idx,
                "similarity": round(similarity, 3),
            })
    return drift_points


def structural_preprocess(text):
    paragraphs = _split_paragraphs(text)
    sentences = _split_sentences(text)
    claim_candidates = _claim_candidates(sentences)
    filler_density = _filler_density(text)
    repetition_score = _repetition_score(sentences)
    clusters = _topic_clusters(paragraphs)
    sentiment = _paragraph_sentiment(paragraphs)
    drift_transitions = []
    for idx in range(1, len(sentiment)):
        delta = abs(sentiment[idx] - sentiment[idx - 1])
        if delta >= 0.7:
            drift_transitions.append({
                "from_paragraph": idx - 1,
                "to_paragraph": idx,
                "sentiment_delta": round(delta, 3),
            })

    return {
        "paragraphs": paragraphs,
        "sentences": sentences,
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "repetition_score": round(repetition_score, 3),
        "filler_density": round(filler_density, 3),
        "topic_clusters": clusters,
        "drift_transitions": drift_transitions,
        "claim_candidates": claim_candidates,
    }


def _extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    raise ValueError("Invalid JSON response")


def _openai_request(messages, model=None, temperature=0.2, timeout=None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.environ.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    timeout = timeout or float(os.environ.get("SLOP_REQUEST_TIMEOUT", "25"))

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 800,
    }

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _run_critic(prompt, text, paragraphs):
    messages = [
        {
            "role": "system",
            "content": "You are a strict JSON generator. Output only valid JSON. No prose.",
        },
        {"role": "user", "content": prompt.format(text=text, paragraphs=paragraphs)},
    ]
    raw = _openai_request(messages)
    return _extract_json(raw)


def _logical_consistency_runs(text, paragraphs, runs):
    prompt = (
        "Analyze the text for contradictions. Return JSON with keys: "
        "contradictions (array of objects with a, b, explanation, paragraph_index), "
        "logical_score (0-100). Text: {text}"
    )
    outputs = []
    for _ in range(runs):
        outputs.append(_run_critic(prompt, text, paragraphs))
    return outputs


def _claim_support_runs(text, paragraphs, runs):
    prompt = (
        "Extract claims and flag unsupported or overconfident claims. "
        "Return JSON with keys: unsupported_claims (array of objects with claim, reason, paragraph_index), "
        "overconfidence_score (0-100), support_score (0-100). Text: {text}"
    )
    outputs = []
    for _ in range(runs):
        outputs.append(_run_critic(prompt, text, paragraphs))
    return outputs


def _topic_drift_runs(text, paragraphs, runs):
    prompt = (
        "Evaluate coherence between paragraphs. Return JSON with keys: "
        "drift_points (array of objects with from_paragraph, to_paragraph, explanation), "
        "coherence_score (0-100). Paragraphs: {paragraphs}"
    )
    outputs = []
    for _ in range(runs):
        outputs.append(_run_critic(prompt, text, paragraphs))
    return outputs


def _filler_runs(text, paragraphs, runs):
    prompt = (
        "Detect filler, vagueness, and buzzwords. Return JSON with keys: "
        "filler_phrases (array), vagueness_score (0-100). Text: {text}"
    )
    outputs = []
    for _ in range(runs):
        outputs.append(_run_critic(prompt, text, paragraphs))
    return outputs


def _score_stats(scores):
    if not scores:
        return 0.0, 0.0
    return mean(scores), pvariance(scores)


def _aggregate_runs(outputs, score_key, default_score=50):
    scores = []
    for output in outputs:
        score = output.get(score_key)
        if isinstance(score, (int, float)):
            scores.append(float(score))
    if not scores:
        scores = [default_score]
    avg, var = _score_stats(scores)
    return avg, var


def _compute_stability(variances):
    if not variances:
        return 0.0
    avg_variance = mean(variances)
    stability = 100 - (avg_variance / 2500 * 100)
    return round(max(0.0, min(100.0, stability)), 2)


def analyze_content(text):
    normalized = _normalize_text(text)
    structural = structural_preprocess(text)
    paragraphs = structural["paragraphs"]

    runs = int(os.environ.get("SLOP_CRITIC_RUNS", "1"))
    runs = max(1, min(runs, 3))

    logical_runs = _logical_consistency_runs(normalized, paragraphs, runs)
    support_runs = _claim_support_runs(normalized, paragraphs, runs)
    drift_runs = _topic_drift_runs(normalized, paragraphs, runs)
    filler_runs = _filler_runs(normalized, paragraphs, runs)

    logical_avg, logical_var = _aggregate_runs(logical_runs, "logical_score")
    support_avg, support_var = _aggregate_runs(support_runs, "support_score")
    coherence_avg, coherence_var = _aggregate_runs(drift_runs, "coherence_score")
    vagueness_avg, vagueness_var = _aggregate_runs(filler_runs, "vagueness_score")

    stability_score = _compute_stability([logical_var, support_var, coherence_var, vagueness_var])

    filler_density_scaled = structural["filler_density"] * 100
    quality_score = (
        0.30 * logical_avg
        + 0.25 * coherence_avg
        + 0.20 * support_avg
        + 0.15 * (100 - filler_density_scaled)
        + 0.10 * stability_score
    )
    slop_score = round(max(0.0, min(100.0, 100 - quality_score)), 2)

    if slop_score >= 80:
        classification = "High Slop"
    elif slop_score >= 60:
        classification = "Mostly Slop"
    elif slop_score >= 40:
        classification = "Mixed"
    else:
        classification = "Low Slop"

    contradictions = logical_runs[0].get("contradictions", []) if logical_runs else []
    unsupported_claims = support_runs[0].get("unsupported_claims", []) if support_runs else []
    drift_points = drift_runs[0].get("drift_points", []) if drift_runs else []
    filler_phrases = filler_runs[0].get("filler_phrases", []) if filler_runs else []

    suggested_rewrites = []
    if os.environ.get("SLOP_ENABLE_REWRITES", "true").lower() in ("1", "true", "yes", "on"):
        suggested_rewrites = _generate_rewrites(
            paragraphs,
            contradictions,
            unsupported_claims,
            drift_points,
            filler_phrases,
        )

    report = {
        "slop_score": slop_score,
        "classification": classification,
        "diagnostics": {
            "logical_consistency": round(logical_avg, 2),
            "coherence": round(coherence_avg, 2),
            "claim_support": round(support_avg, 2),
            "filler_density": round(filler_density_scaled, 2),
            "vagueness": round(vagueness_avg, 2),
            "stability": stability_score,
        },
        "contradictions": contradictions,
        "unsupported_claims": unsupported_claims,
        "drift_points": drift_points,
        "filler_phrases": filler_phrases,
        "structural_signals": {
            "sentence_count": structural["sentence_count"],
            "paragraph_count": structural["paragraph_count"],
            "repetition_score": structural["repetition_score"],
            "filler_density": structural["filler_density"],
            "topic_clusters": structural["topic_clusters"],
            "drift_transitions": structural["drift_transitions"],
        },
        "suggested_rewrites": suggested_rewrites,
    }
    return report


def _generate_rewrites(paragraphs, contradictions, unsupported_claims, drift_points, filler_phrases):
    target_indices = set()
    for item in contradictions:
        idx = item.get("paragraph_index")
        if isinstance(idx, int):
            target_indices.add(idx)
    for item in unsupported_claims:
        idx = item.get("paragraph_index")
        if isinstance(idx, int):
            target_indices.add(idx)
    for item in drift_points:
        idx = item.get("to_paragraph")
        if isinstance(idx, int):
            target_indices.add(idx)

    target_indices = sorted(i for i in target_indices if 0 <= i < len(paragraphs))
    if not target_indices:
        return []

    suggestions = []
    limit = int(os.environ.get("SLOP_REWRITE_LIMIT", "2"))
    limit = max(0, min(limit, 5))
    for idx in target_indices[:limit]:
        paragraph = paragraphs[idx]
        prompt = (
            "Rewrite the paragraph to remove filler, add a concrete example, "
            "remove unsupported claims, and improve logical flow. "
            "Return JSON with keys: original, revised, changes_explained (array). "
            "Paragraph: {paragraph}"
        )
        try:
            output = _run_critic(prompt, paragraph, paragraphs)
        except Exception:
            continue
        if output.get("original") and output.get("revised"):
            output["paragraph_index"] = idx
            suggestions.append(output)
    return suggestions
