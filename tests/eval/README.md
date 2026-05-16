# Eval cases

Fixed cases the Company Researcher (and later agents) are judged against.
Created in F02 to satisfy Golden Rule #4 (an agent needs a prompt file AND
>=2 eval cases before it is built). Automated scoring lands in F07 — for now
these are run BY HAND via the smoke test (swap the URL) and graded against
`expected_dimensions`.

## Case format

```yaml
input:
  source_type: url            # url | pdf
  source_ref: https://...     # what intake receives
expected_dimensions:          # human-checkable pass/fail bullets
  - "..."
notes: |
  Why this case exists / difficulty tier.
```

## Difficulty tiers (deliberate spread)

- **stripe** — famous, data-rich. If this fails, prompts are deeply broken.
- **modal_com** — mid-known, well-documented but smaller.
- **obscure_ycombinator** — long-tail honesty test: the agent must admit
  thin sources rather than hallucinate. This is the case that matters most.

## Grading (manual, F02)

Run the smoke test against each `source_ref`, read the output, mark each
`expected_dimension` pass/fail, record in `my_work/learnings.md`. Do NOT
relax a dimension to make it pass (Golden Rule #6).
