# Raw sources for the real-document test set

These are the untouched source materials `bench/real_text_questions.jsonl` was hand-built from
(see [bench/REAL_QUESTIONS.md](../REAL_QUESTIONS.md) for how). Nothing here is edited except
`leases/*.txt`, which were pulled from HTML filings and stripped of markup only.

- **`usajobs_raw.jsonl`** — 32 real U.S. federal job postings, one JSON object per line. Pulled from
  [USAJOBS](https://www.usajobs.gov/) announcement text via the open
  [abigailhaddad/usajobs-scraping](https://huggingface.co/datasets/abigailhaddad/usajobs-scraping)
  dataset. U.S. government work product: public domain.
- **`leases/*.txt`** — 4 real commercial lease documents, each a company's own exhibit filed with the
  SEC, found through [EDGAR full-text search](https://www.sec.gov/edgar/search/):
  - `penumbra_saltlake.txt` — Penumbra, Inc., Salt Lake City warehouse lease
  - `axogen_commercial.txt` — Axogen, Inc., Burleson TX commercial lease amendment
  - `xtant_medical.txt` — Xtant Medical Holdings, Inc., Belgrade MT lease
  - `sumo_logic.txt` — Sumo Logic, Inc., Redwood City sublease

  SEC filings are public record.
