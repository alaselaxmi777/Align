# ALIGN Maharashtra synthetic dataset v3.0

ALL records are synthetic (`is_synthetic: true`). Dev and evaluation only. Never load into production. Places are intentionally absent (use Google Places).
User names are random first-name + surname combinations and may coincide with real people. Never treat them as real or show them as real accounts.

| File | Records | Notes |
|---|---|---|
| synthetic_communities.json | 400 | 42 topics, 13 Maharashtra cities, English / Marathi / Hinglish descriptions |
| synthetic_events.json | 800 | includes local events (kabaddi, kavi sammelan, garba, fort treks, MPSC mock tests...), past and upcoming |
| synthetic_activities.json | 500 | |
| synthetic_users.json | 1500 | Maharashtrian-style names, languages (Marathi/Hindi/English), occupations, no emails, no minors |
| synthetic_interactions.json | 19,990 | view / save / join_or_register / feedback |
| eval_queries.json | 334 | English 235, Marathi (Devanagari) 49, Hinglish 50. dev/test split 241/93 |
| ground_truth_topics.json | | Evaluation code only. Never feed to the recommender. |
| taxonomy_maharashtra.json | | Base taxonomy + Maharashtra topics, Marathi first in languages, city list |
| clusters_base.py + generate_maharashtra_dataset.py | | Reproducible: `python generate_maharashtra_dataset.py <output_dir>` (needs ../align_dataset/taxonomy.json for the merged taxonomy) |

## IMPORTANT: embedding model
Marathi and Hinglish queries need a MULTILINGUAL model, for example `paraphrase-multilingual-MiniLM-L12-v2` or `LaBSE`. English-only models such as `all-MiniLM-L6-v2` will do poorly on Devanagari. Compare both in your ablation: that is a good result for the report.

## Labels
2 = same topic, 1 = related topic. Rule-based, author-written, not produced by the model under test. NDCG uses 0/1/2. Precision@k and MRR count only 2. Tune on `dev`, report on `test`.

## Limitations (state in the report)
- Text is template-generated. Some titles read awkwardly (e.g. "Hands-on Jam Sessions Session"). Marathi and Hinglish text is simple and formulaic, not natural user writing.
- Hinglish and Marathi text was written by an AI and not reviewed by a native speaker. Have a Marathi speaker check it before you report multilingual results.
- Cities and coordinates are real, approximate and city-level. Communities, events and people are invented.
- Interactions are simulated (72% on-topic, 28% noise).
