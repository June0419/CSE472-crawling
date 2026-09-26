# LLM-Assisted Keyword Analysis

## Scope

- Disaster: 2025 Palisades Fire
- Source instance: https://mastodon.social
- Analysis sample: 500 posts collected directly from the selected hashtag timelines
- Context-only replies were excluded from keyword frequency so they do not change the requested post sample.

## LLM prompt and procedure

**Model used:** OpenAI Codex (GPT-5), in the project-development session.

**Prompt:** “Review the frequency-ranked unigrams and bigrams from public Mastodon posts about the 2025 Palisades Fire. Merge surface variants into clear disaster-related concepts, remove URL/platform artifacts, and retain interpretable themes covering the event, places, impacts, response, recovery, community, and policy. Do not infer sentiment or facts that are not present in the text. For every concept, provide transparent matching variants so its support can be counted reproducibly.”

The LLM was used for semantic grouping, not for inventing counts. `src/analyze_content.py` records each concept's regular-expression patterns and counts how many distinct posts contain at least one pattern. This lets the result be audited and rerun.

## Top themes

| Rank | Keyword/theme | Matching posts | Share | Group |
|---:|---|---:|---:|---|
| 1 | Palisades Fire | 482 | 96.4% | event |
| 2 | Eaton Fire | 252 | 50.4% | event |
| 3 | Los Angeles | 179 | 35.8% | place |
| 4 | Wildfire | 170 | 34.0% | hazard |
| 5 | Malibu | 72 | 14.4% | place |
| 6 | Rain & Storm | 67 | 13.4% | hazard |
| 7 | California | 65 | 13.0% | place |
| 8 | Evacuation | 54 | 10.8% | response |
| 9 | Debris Flow & Flooding | 52 | 10.4% | hazard |
| 10 | Homes & Property | 51 | 10.2% | impact |
| 11 | Pacific Palisades | 49 | 9.8% | place |
| 12 | Damage & Loss | 48 | 9.6% | impact |
| 13 | Burn Scar | 36 | 7.2% | hazard |
| 14 | Recovery & Rebuilding | 29 | 5.8% | recovery |
| 15 | Government & FEMA | 25 | 5.0% | cause & policy |

## Interpretation

The largest themes show what the collected posts mention most often; they do not measure approval, sentiment, or causal importance. Counts can overlap because one post may mention several themes. Results apply only to the collected public posts visible through the selected Mastodon instance and hashtags.
