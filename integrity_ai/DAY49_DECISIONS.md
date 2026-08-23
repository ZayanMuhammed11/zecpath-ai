# Day 49 Decisions — integrity_ai/

## 1. No event-capture logic; caller-supplied placeholders only

This module contains **zero** browser tab-switch detection, screen
focus tracking, audio voice detection, or gaze tracking logic. All
four event counts on `IntegrityEvents` (`tab_switch_count`,
`focus_loss_count`, `external_voice_count`, `gaze_deviation_count`)
are caller-supplied placeholders, pending a future browser/audio/
video-tracking implementation. No event-capture pipeline exists
anywhere in this codebase yet.

## 2. Module isolation confirmed

`integrity_ai/` has zero imports from any other project module,
including `interview_ai/`, `technical_ai/`, `screening_ai/`,
`ats_engine/`, `scoring/`, `decision_ai/`, and `visual_behavior_ai/`
(Day 48). Any shared-looking constant or helper pattern (e.g. the
missing-key `ValueError` message style, or the weighted-sum scoring
shape) is duplicated by value where it appears in this module, never
imported cross-module.

## 3. Deliberately unwired this day

This module is **not** wired into `decision_ai/`, `visual_behavior_ai/`,
any summary generator, or any other scoring system. It produces one
self-contained scoring capability only, matching the "deliberately
unwired, single day's scope" precedent already established for
`visual_behavior_ai/` (Day 48) and `technical_ai/` (Days 46-47).

## 4. EVENT_CAPS vs WARNING_THRESHOLDS — two distinct constants

`EVENT_CAPS` (normalization denominators — the count at which a
signal's sub-score bottoms out at 0.0) and `WARNING_THRESHOLDS`
(warning trigger points — the count that must be strictly exceeded
before a warning is emitted) are two distinct constants for two
distinct purposes. Every function in `integrity_scoring.py` reads
from exactly one shared constant per purpose: `_normalize_signal`
consumes a cap sourced from `EVENT_CAPS`, and
`generate_integrity_warnings` consumes thresholds sourced from
`WARNING_THRESHOLDS`. No function defines or compares against a
function-local duplicate threshold value.

This directly corrects an inconsistency identified in this day's
reviewed manager sample, where tab-switch threshold values disagreed
across two functions (3 vs 2). In this implementation, every check of
the tab-switch (or any other) threshold reads from the same
`WARNING_THRESHOLDS` dict entry, so that kind of drift is structurally
impossible.

## 5. `get_integrity_risk_level` polarity

**HIGHER `integrity_score` means LOWER risk.** This is documented
explicitly here (and in the model/function docstrings) to prevent
future confusion, since it is an inverted-scale label relative to raw
score magnitude: a score of 90 is *good* (Low Risk), not alarming.

## 6. No `random` module usage

No use of the `random` module anywhere in this module, matching the
project-wide determinism rule.
