# Data Exclusions

This document explains why part of the data in this dataset is excluded, the exclusion criterion, and the exact list.

## Dataset overview

- While watching 5 emotion-eliciting films (Anger / Sadness / Neutral / Contentment / Amusement; presentation order counterbalanced across participants), each participant was recorded with synchronized thermal imaging of the **frontal face** and **one (right) ear** (FLIR A655sc; two cameras recording simultaneously).
- Continuous (per-second) self-reported valence / arousal was collected in parallel.

Files in this folder:

| File | Contents |
|---|---|
| `simTime.csv` | Start/end second of each film, per participant (**ear-camera timeline**) |
| `va_au_long_autism_group_normal_autistic_traits.csv` | Per-second valence / arousal (and AUs), by participant / film / group |
| `2025～26参加者情報改.xlsx` | Participant info (id / age / sex / counter = presentation order) |
| `exclude_segments.csv` | Exclusion list (machine-readable) |

## Why some data are excluded

The face and the ear were captured by **two independent cameras**, both started manually. The two cameras' clocks are synchronized (they were stopped together; per-participant end times differ by ≤ 4 s), but they were **started at different times**: the ear camera was always started first, and the face camera a little later (4–136 s later, depending on the participant).

The film timeline (`simTime`) is defined on the **ear camera** (a film's onset = seconds after the ear recording started). For most participants the face camera was already recording before the first film began, so it captured everything. For a few participants, however, the face camera **started only after the first film had already begun**, so the **opening portion of that first film has no face footage** — the footage is genuinely missing (the camera was not yet recording), it is not a misalignment. The ear camera covered the entire session for every participant.

## Exclusion criterion

This dataset is intended for **paired face + ear analysis**, where every data point must be a simultaneous face + ear pair. Therefore:

> **If the face camera missed ≥ 5 s of a film, that film is excluded for BOTH the ear and the face for that participant. A gap < 5 s is treated as negligible and kept. Only the affected single film is excluded — never the whole participant; all other films are kept.**

## Excluded segments

Each of the following 6 participants has their **first film** excluded (`exclude_segments.csv` is the machine-readable version):

| Participant | Excluded film | Start–end (s, ear timeline) | Face missing (s) |
|---|---|---|---|
| 251110_01 | Neutral | 35 – 184 | 85.8 |
| 251106_02 | Sadness | 54 – 225 | 82.0 |
| 251111_01 | Contentment | 25 – 225 | 80.9 |
| 251107_01 | Neutral | 40 – 189 | 64.9 |
| 251106_01 | Contentment | 103 – 303 | 18.5 |
| 251218_01 | Amusement | 13 – 208 | 5.4 |

7 other participants had a face gap < 5 s (0.1–3.6 s) and are kept.

`exclude_segments.csv` columns: `Participant_ID, exclude_film, film_start_earSec, film_end_earSec, front_missed_s`.

## How to apply

1. From `simTime.csv`, get each film's start/end second (ear timeline).
2. From `exclude_segments.csv`, take the listed (participant, film) combinations and mark them excluded for **both the ear and the face**.
3. Use all other (participant, film) combinations in the analysis.
