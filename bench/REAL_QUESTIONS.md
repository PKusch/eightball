# Real-document test set

**What it is.** 129 items in `bench/real_text_questions.jsonl`, same format as
`bench/text_questions.jsonl`: a short text, one yes/no question, and a label the ball must
guess:

- **yes**: the text says so.
- **no**: the text says the opposite.
- **maybe**: the text never says.

Unlike the templated set, every text here is a real excerpt from a real document, and every
question was written by hand after reading that excerpt. Nothing was generated from a
formula, so this set is small and will only grow by more hand reading, not by running a
script.

**The two sources.**

- **32 U.S. federal job postings** (`bench/real/usajobs_raw.jsonl`), pulled from USAJOBS.
  These are U.S. government work product and are public domain, so nothing about using them
  is restricted.
- **4 real commercial leases** (`bench/real/leases/*.txt`): a sublease (Sumo Logic /
  Delphix, Redwood City), a warehouse lease (Penumbra, Salt Lake City), a lease amendment
  (Axogen, Burleson TX), and a triple-net lease (Bacterin/Xtant Medical, Belgrade MT). All
  four are exhibits companies filed with the SEC, which makes them public record.

**How the excerpts were picked.** For each job posting I trimmed the "Click here" navigation
boilerplate and kept a few hundred words of the actual job summary and duties. For each
lease I picked 1-3 short passages (a paragraph or a few clauses) covering things like the
address, square footage, rent schedule, security deposit, permitted use, or a maintenance
clause. Each lease passage counts as its own "document" here, the same way each job posting
does.

**How the questions were written.** For every excerpt I read the kept text and asked 2-3
questions about facts stated in it — never about a field from the structured USAJOBS data (like
"clearance required: Y") unless that same fact also appears in words in the excerpt. For
"maybe" questions I picked a topic the excerpt genuinely never touches (checked by search,
not by memory), for example asking about telework on a posting that never mentions telework
at all.

**How labels were checked** (`python bench/check_real_text_questions.py`). Because these are
hand-written, not built from a fact table, a label can't be worked out again from a formula
the way it can for the templated set. Instead every item carries a `facts` field with the
exact phrase(s) that ground its label:

- for "yes" and "no" items, `facts.present` lists the phrase(s) that must appear in the text
  — the checker confirms they do;
- for "maybe" items, `facts.absent` lists the phrase(s) that must NOT appear in the text —
  the checker confirms they don't.

That catches the mechanical failure (a question about a fact the excerpt doesn't actually
contain), but it can't catch a misreading — an excerpt saying one thing and me writing down
the wrong label anyway. So after the checker passed, I read all 129 items myself, one at a
time, text and question and label together, and asked whether I could defend the label to a
stranger who only sees the text and the question. One question had unclear wording ("will
stay open ... at the latest") and was reworded for clarity; everything else held up.

**Splits.** 45 dev, 84 test (about a third dev, matching the templated set's ratio), split
separately within each kind and label so both splits have examples of everything.

**Real counts.**

| kind | yes | no | maybe | total |
|------|-----|-----|-------|-------|
| job_real (USAJOBS) | 36 | 34 | 26 | 96 |
| lease_real (leases) | 18 | 4 | 11 | 33 |
| **all** | **54** | **38** | **37** | **129** |

That's short of an even 3-way split (42% / 29% / 29%), mostly because the lease documents
gave few clean chances to write a "no" question — most facts a lease states plainly (an
address, a rent figure, a deposit) don't have a natural "opposite" stated nearby the way a
job posting's "Telework: Not Available" does.

**Known limits, honestly.**

- **Small and hand-built.** 129 items versus 600 in the templated set. Growing this set
  means reading more real documents by hand; there's no generator to point at a bigger
  number.
- **Leases are messy.** Real filed exhibits carry page furniture, DocuSign artifacts, and
  (for the Axogen lease) a fill-in-the-blank form whose answers were extracted out of order
  by whatever turned the PDF into text. I reconstructed the filled-in values back into their
  blanks by hand for that one lease; the numbers are real, but the passage reads more like a
  form than a sentence.
- **Job postings repeat themselves.** Federal job ads share a lot of boilerplate language
  across agencies — "Telework: Not Available", "Permanent Change of Station: Not
  Authorized", "This is not a virtual position" — so a chunk of the "no" questions lean on
  that same handful of stock phrases rather than on duty-specific text. About a third of the
  "no" job questions are also built by negating a "yes" fact ("Is X excluded from this
  role?" when the text says X is included) rather than by finding a naturally stated
  opposite; each one is still grounded in an explicit sentence, but the phrasing is more
  contrived than a job posting would use on its own.
- **"Maybe" leans on a short list of topics** (security clearance, telework, travel, salary
  amount, a specific dollar figure) reused across different postings with different wording.
  The topic is genuinely absent from each excerpt, but a model could learn "these topics are
  usually maybe" rather than reading the text.
- **No trap items.** The templated set plants the occasional wrong-topic number as a trap for
  keyword matching. This set doesn't; a lucky keyword-matcher could do better here than its
  real understanding warrants.
