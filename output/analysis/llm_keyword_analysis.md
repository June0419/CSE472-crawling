# Per-Post LLM Keyword Analysis

## Method

- Model: Llama 3.2 3B, instruction-tuned Q4_K_M build served locally by Ollama
- Input: 500 posts collected directly from the selected hashtag timelines
- Output: exactly three distinct keywords for every post (1,500 raw keyword assignments)
- Generation: temperature 0 with a required JSON schema
- Privacy: inference ran locally; post text was not sent to a hosted LLM API

## Exact system prompt

```text
You are a precise content-analysis assistant for a disaster social-media study.
For every Mastodon post, return exactly three distinct, concise English keywords or short phrases that are explicitly supported by the post.

Prioritize disaster-related named events, affected places, hazards, impacts, emergency response, recovery, policy, and community actions. Use 1-3 words per keyword. Expand compressed hashtags and never split a proper name across separate keywords: #PalisadesFire becomes "palisades fire", #EatonFire becomes "eaton fire", and #LosAngeles becomes "los angeles". Do not return isolated fragments such as "los", "angeles", "palisades", "eaton", or the generic word "fire" when the post states a more specific event or place.

Example: a post saying "LA County sues State Farm over wildfire claims #EatonFire #PalisadesFire #insurance" should return ["eaton fire", "palisades fire", "insurance claims"]. A post saying "Palisades Fire burns in Los Angeles during a windstorm" should return ["palisades fire", "los angeles", "windstorm"].

Normalize obvious variants to a consistent form. Ignore URLs, account names, platform terms, engagement requests, timestamps, and non-topical boilerplate. Do not infer sentiment, causes, or facts that the post does not state. Return only data matching the supplied JSON schema.
```

## Sample outputs

| # | Post excerpt | Three generated keywords |
|---:|---|---|
| 1 | Historic Malibu Winery Closes After Losing Tasting Room to Palisades Fire #Lifestyle #LifestyleNews #Malibu #PalisadesFire #Wine #Winesandsp | malibu winery; palisades fire; wines and spirits |
| 2 | Via Supervisor Barger: "Fire survivors, in partnership with a UCLA research team, are building the nation’s first public record of which ins | eaton fire; palisades fire; insurer claims |
| 3 | LA Times: L.A. County sues State Farm over its handling of wildfire claims #wildfires #EatonFire #PalisadesFire #insurance #disaster | la county; palisades fire; state farm |
| 4 | 91 years ago, we lost #WillRogers. 16 years ago, I made a real bucket-list trip to the 1935 crash site near distant Barrow, Alaska. Despite  | will rogers; palisades fire; alaska |
| 5 | Billionaire Rick Caruso Brings Back Palisades Village After Wildfire: “This Is One Chapter of the Comeback Story” #Business #BusinessNews #P | palisades village; palisades fire; rick caruso |

## Most frequent keywords

| Rank | Keyword | Frequency | Share of posts |
|---:|---|---:|---:|
| 1 | palisades fire | 419 | 83.8% |
| 2 | eaton fire | 146 | 29.2% |
| 3 | los angeles | 142 | 28.4% |
| 4 | wildfire | 84 | 16.8% |
| 5 | malibu | 31 | 6.2% |
| 6 | evacuation | 28 | 5.6% |
| 7 | los angeles fires | 28 | 5.6% |
| 8 | hughes fire | 16 | 3.2% |
| 9 | rain | 13 | 2.6% |
| 10 | california | 11 | 2.2% |
| 11 | pacific palisades | 11 | 2.2% |
| 12 | franklin fire | 8 | 1.6% |
| 13 | insurance | 8 | 1.6% |
| 14 | fema | 7 | 1.4% |
| 15 | debris flow | 7 | 1.4% |

## Interpretation

The frequency distribution highlights the focal Palisades Fire discussion while also showing recurring references to Los Angeles locations, the Eaton Fire, evacuation, fire impacts, weather, and post-fire recovery. A sparse tail of terms such as Will Rogers, Volkswagen, and Palestine is unexpected in a disaster-focused sample and exposes cross-topic hashtag reuse or incidental references; those terms were retained instead of being manually filtered. Because each post contributes exactly three keywords, a term's frequency is also the number of sampled posts assigned that theme after transparent spelling normalization. The output summarizes themes; it does not measure sentiment or factual accuracy.
