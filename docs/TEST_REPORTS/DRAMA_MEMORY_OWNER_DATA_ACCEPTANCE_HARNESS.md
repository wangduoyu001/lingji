# Drama Memory Owner-Data Acceptance Harness

## 1. Purpose

This harness closes the measurement gap between synthetic Drama Memory tests and real-script acceptance.

It does not claim that the real-data gates have passed. It provides a reproducible runner that can prove or reject them with owner-supplied scripts and questions.

Target gates:

```text
real dramas >= 10
owner questions >= 100
retrieval accuracy >= 85%
character accuracy >= 90%
episode-event accuracy >= 85%
```

Writer Agent remains disabled until these gates and installed Desktop acceptance pass.

## 2. Files

```text
src/plugins/drama_intelligence/acceptance.py
scripts/run_drama_acceptance.py
tests/test_drama_acceptance.py
```

The runner reuses `DramaService.search()`. It does not introduce another retrieval stack, database, embedding configuration, queue or permanent memory source.

## 3. Safety boundary

The CLI hard-refuses every workspace except `acceptance`.

```text
production data: not required
production Drama collection: not required
personal Memory Engine: unchanged
second_brain/: unchanged
Writer Agent: unchanged and disabled
```

There is no production override in the acceptance runner.

## 4. Question dataset

The dataset is UTF-8 JSONL, one question per line.

Required fields:

```json
{
  "id": "q001",
  "query": "女主在哪一集公开继承人身份？",
  "expected": {
    "contains_any": ["公开继承人身份"],
    "characters": ["林晚"],
    "episode_numbers": [8]
  }
}
```

At least one retrieval label is mandatory:

```text
drama_ids
drama_titles
source_refs
source_ref_prefixes
contains_any
contains_all
```

Optional secondary labels:

```text
characters
episode_numbers
```

Optional query controls:

```text
limit
drama_id
chunk_type
```

The runner rejects questions that only contain character or episode labels because those labels cannot independently prove that the correct bridge or source was retrieved.

## 5. Metrics

For every question the runner records:

```text
Top-K retrieval hit
Top-1 hit
matched rank
matched chunk
matched Drama
matched source_ref
citation validity
character correctness
episode correctness
search latency
semantic-degradation warning codes
```

Aggregate evidence includes:

```text
retrieval accuracy
Top-1 accuracy
citation accuracy
character accuracy
episode-event accuracy
latency mean / p50 / p95 / max
dataset SHA256 fingerprint
Drama read-model revision
workspace and semantic state
```

A missing character-labeled or episode-labeled denominator fails the corresponding gate instead of silently reporting success.

## 6. Execution

Configure LingJi to use the `acceptance` workspace, then run:

```powershell
python scripts/run_drama_acceptance.py `
  --scripts "E:\drama-acceptance\scripts" `
  --questions "E:\drama-acceptance\questions.jsonl" `
  --recursive `
  --output-dir "output\drama-acceptance"
```

The script can also evaluate already imported Drama data by omitting `--scripts`.

Exit codes:

```text
0 = all gates passed
2 = validation failed, dataset invalid or workspace unsafe
```

## 7. Evidence output

The runner writes timestamped immutable-style evidence files:

```text
output/drama-acceptance/drama-acceptance-<UTC>.json
output/drama-acceptance/drama-acceptance-<UTC>.md
```

The JSON retains per-question results for diagnosis. The Markdown report stays concise and lists failed retrieval questions.

## 8. Automated contract

`tests/test_drama_acceptance.py` verifies:

```text
JSONL parsing
unscorable-question rejection
Top-K and Top-1 scoring
citation scoring
character scoring
episode scoring
threshold gates
semantic warning capture
JSON/Markdown evidence creation
```

Synthetic tests validate the harness contract only. They do not replace the owner-data run.

## 9. Remaining work after this harness

```text
run 10 real scripts in acceptance workspace
author and review 100 labeled questions
archive generated JSON/Markdown evidence
fix parsing or retrieval below threshold
run installed Desktop Drama full-control acceptance
only then consider Writer Agent
```
