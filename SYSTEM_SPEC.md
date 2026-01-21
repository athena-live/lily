# System Spec: lily

Source seed (README):
"Software design framework for identifying AI slop, outputs that look valid but fail under structure, logic, or execution."

## 1. Purpose & Scope

Goal:
Detect, classify, and explain AI slop: content that appears coherent but collapses under formal structure, logical consistency, or real execution.

Non-goal:
This is not an AI-detector (human vs AI). It evaluates output quality and validity, not authorship.

## 2. Core Functional Requirements

FR-1: Input Ingestion

- Accept inputs as:
  - Plain text
  - Code snippets (language-tagged)
  - Structured docs (Markdown, JSON, YAML)
- Support batch and single-item analysis
- Preserve original formatting and metadata

FR-2: Structural Integrity Analysis

The system must evaluate whether output conforms to its claimed structure.

Required checks:
- Syntax validity (language-aware)
- Schema adherence (JSON/YAML/XML)
- Section completeness (e.g., headings referenced but missing)
- Internal reference resolution (links, variables, functions)

Output:
- Structural pass/fail
- List of violations with exact locations

FR-3: Logical Consistency Analysis

The system must detect internal contradictions and logical failures.

Required checks:
- Self-contradicting statements
- Invalid assumptions carried across steps
- Circular reasoning
- Undefined terms used as primitives
- Causal claims without dependency support

Output:
- Logical confidence score
- Enumerated contradiction graph

FR-4: Executability & Verifiability

The system must attempt to validate whether claims or instructions can be executed.

Required checks:
Code:
- Dry-run / static analysis
- Dependency resolution
- Function reachability

Procedures:
- Missing steps
- Impossible ordering

Claims:
- Falsifiable vs non-falsifiable
- Testable vs narrative

Output:
- Executable / Non-Executable classification
- Failure reason taxonomy

FR-5: Information Density & Signal Ratio

The system must detect low-signal, high-verbosity patterns.

Required checks:
- Redundant phrasing detection
- Semantic loops
- Placeholder abstractions ("robust", "scalable", "leveraging")
- Token-to-fact ratio

Output:
- Signal-to-Noise score
- Highlighted slop segments

FR-6: Claim-Support Mapping

The system must map claims to evidence or mechanisms.

Required checks:
Each declarative claim must have:
- A definition
- A mechanism
- Or a reference

Flag:
- Orphan claims
- Vague authority appeals
- Unanchored generalizations

Output:
- Claim graph with support edges
- Unsupported claim list

FR-7: Hallucination Risk Indicators

The system must identify patterns strongly correlated with hallucination.

Required indicators:
- Confident tone + low verifiability
- Over-specific but uncheckable facts
- Named entities without context
- Invented standards, tools, or APIs

Output:
- Hallucination likelihood score
- Risk explanation (non-probabilistic language)

FR-8: Slop Classification Engine

The system must classify failure modes.

Minimum classes:
- Structural Slop
- Logical Slop
- Execution Slop
- Semantic Slop
- Narrative Padding
- Mixed / Compound Slop

Output:
- Primary and secondary slop types
- Confidence levels

FR-9: Explainability & Traceability

The system must explain why something is slop.

Requirements:
- Line-level annotations
- Deterministic reasoning paths
- No opaque "model says so" outputs

FR-10: Scoring & Verdict

The system must produce a clear verdict.

Required outputs:
- Slop Score (0-100)
- Pass / Warn / Fail
- "Why this fails in practice" summary

## 3. Interfaces & Integration

FR-11: API Access

- REST + JSON
- Deterministic mode (no randomness)
- Webhook support for CI/CD

FR-12: Developer Tooling

- CLI tool for:
  - Code review
  - PR gating
  - IDE plugin hooks (read-only annotations)

## 4. Constraints & Guardrails

FR-13: Determinism

- Same input -> same output
- No stochastic scoring in final verdict

FR-14: Model-Agnostic Design

Must analyze outputs from:
- Any LLM
- Humans
- Hybrid systems

FR-15: Zero Trust Posture

- Assume output is wrong until verified
- No "benefit of the doubt" scoring

## 5. Non-Functional (Brief)

- Latency target: <2s per 5k tokens
- All failure modes must be reproducible
- Logs must support post-mortem analysis

## 6. Definition of "AI Slop" (Operational)

AI slop is output that optimizes for plausibility rather than correctness, and collapses when structure, logic, or execution is enforced.
