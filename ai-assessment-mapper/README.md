# AI Assessment Mapper

An AI-powered web app that lets a teacher upload a question paper and a
student's handwritten answer sheet, automatically extracts every question and
every handwritten answer, maps answers to questions, and lets the teacher
click any question to see the **exact region** of the answer sheet where that
answer was written — highlighted, on the correct page, at any zoom level.

```
Question Paper ──▶ Question Extraction ──┐
                                          ├─▶ Mapping ──▶ Validation ──▶ Interactive Viewer ──▶ (optional) AI Grading
Answer Sheet ────▶ Answer Extraction ─────┘
```

## Architecture

Three independently deployable services, strictly layered — the frontend
never talks to the AI provider, and the backend never contains an AI prompt.

```
React (JS, Vite, Tailwind)
        │  REST / axios
        ▼
Node.js / Express  (API gateway, uploads, temp storage, orchestration)
        │  REST / axios (multipart)
        ▼
Agentic AI (Python, FastAPI)  (agent pipeline)
        │
        ▼
Vision AI model (OpenRouter openai/gpt-4o, vision + forced function-calling)
```

- **frontend/** — React + JavaScript only (no TypeScript). Upload UI,
  processing screen, and the question/answer viewer with normalized-coordinate
  highlighting.
- **backend/** — Express API gateway. Handles uploads (Multer), temp file
  lifecycle, and forwards documents to the agentic AI service. Contains no AI
  prompts or provider logic.
- **agentic-ai/** — FastAPI service organized as an agent pipeline (not ad-hoc
  API calls). The only code that talks to the vision model lives in
  `vision_service.py`.

## Folder structure

```
ai-assessment-mapper/
├── frontend/           React (JS) - upload, processing, assessment UI
├── backend/             Express API gateway
├── agentic-ai/          FastAPI agentic pipeline
├── docker-compose.yml
└── README.md
```

See inline comments in each service for the detailed subfolder layout
(controllers/services/routes on the backend; agents/workflows/prompts/schemas
on the AI service; pages/components/services/hooks on the frontend).

## Agentic AI pipeline

```
                 Assessment Workflow
                         │
        ┌────────────────┴────────────────┐
        ▼                                  ▼
Question Extraction Agent          Answer Extraction Agent
        │                                  │
     Questions[]                       Answers[]
        └────────────────┬─────────────────┘
                          ▼
                   Mapping Agent
                          ▼
                  Validation Agent
                          ▼
                 Assessment Result
                          │
                 (on demand) Grading Agent
```

- **question_extraction_agent** — reads the rendered question-paper pages and
  extracts every question (including sub-parts like `11(a)`, `26(ii)`, and
  nested `11(a)(i)`), preserving printed numbering and page. Long documents
  are split into **overlapping chunks** (see below) before extraction, then
  deterministically deduplicated and merged back together. A deterministic
  post-processing step also catches multiple-choice questions the model
  mis-split into separate sub-questions - e.g. `"The HCF of 96 and 404 is:
  (a) 4 (b) 8 (c) 12 (d) 16"` extracted as four questions `1(a)`..`1(d)`,
  each needing its own answer, when a student actually answers an MCQ by
  picking ONE option. Prompt instructions alone were tested and found
  unreliable for this (confirmed live: the model still split it after being
  told the exact rule); the real fix groups sequentially-lettered siblings
  under one parent and merges them back into a single question only when
  their *content* also looks like options - a shared stem differing by a
  short 1-2 word tail value, with no instruction verb of its own - never on
  label shape alone, since genuine sub-parts commonly use the same a/b/c/d
  labels too (e.g. `"21(i) Find the probability the sum is 7"` /
  `"21(ii) ...is a prime number"` are correctly left as two questions,
  because their shared stem itself contains the instruction word "Find").
- **answer_extraction_agent** — reads the rendered answer-sheet pages and
  extracts every handwritten answer with a confidence score and one or more
  normalized bounding-box regions. Also chunked for long documents, with a
  deterministic merge step that reconstructs answers spanning a chunk
  boundary from the union of every chunk's partial view - it never silently
  drops a page just because it fell on a seam.
- **mapping_agent** — matches answers to questions through a strict priority
  ladder: exact number → normalized number (`Q11(a)`, `11 (a)`, `11-A` all
  resolve the same) → fuzzy string match → semantic/content match via the
  model (last resort, given only the still-unmatched candidates - it can
  never invent a number) → otherwise the mapping is kept but explicitly
  labeled `low-confidence`. A mapping is never silently presented as confident.
- **validation_agent** — flags duplicate/missing questions, invalid pages,
  degenerate bounding boxes, unmatched answers, unanswered questions, and
  low-confidence mappings.
- **rubric_agent** — builds a per-question marking rubric (2-5 weighted
  criteria + a reference answer) from the question alone (`source: "ai"`).
  Criteria marks are deterministically rescaled in Python to sum exactly to
  the question's marks - the model is never trusted to get that arithmetic
  right.
- **grading_agent** (optional) — only runs when the teacher clicks "Grade
  with AI". Grades **criterion-by-criterion** against the rubric, with the
  student's actual answer image (cropped from the original page, not just
  its transcription) attached when available. The model never states a
  final score - every award is clamped to `[0, criterion.max]` in Python and
  the total is a Python sum, so a scoring answer can never exceed its
  maximum regardless of what the model returns. Also flags suspected
  topic mismatches (an answer that appears to address a different question
  entirely) and forces those to zero.

All prompts live in `agentic-ai/app/prompts/`, one file per agent — agents
never inline giant prompt strings. All AI provider calls go through
`agentic-ai/app/services/vision_service.py`; swapping providers means editing
that one file (this has been exercised in practice repeatedly, not just
designed for - the provider has moved between Anthropic, OpenAI direct,
Gemini's OpenAI-compatible endpoint, and OpenRouter during development,
each time touching only that file, `requirements.txt` (when a new SDK was
briefly tried), and `.env`).

## Chunked document processing

Sending an entire long document in a single vision request risks the model
confusing two structurally-similar questions that are many pages apart (this
was an observed real failure, not a hypothetical - a probability question's
answer got attributed to an unrelated geometry question elsewhere in the
same document). `app/services/chunking.py` splits any document longer than
`EXTRACTION_CHUNK_SIZE` pages (default 3) into overlapping chunks
(`EXTRACTION_CHUNK_OVERLAP` pages of overlap, default 1) before extraction.
Short documents are never chunked - one request, byte-for-byte the same
behavior and cost as before.

Adjacent chunks can each independently detect the same content on their
shared overlap page(s). A deterministic merge step (not an AI call) then:
- **Questions**: dedupes by normalized number, keeping the most complete
  extraction if the same question was seen twice.
- **Answers**: takes the **union** of every region seen across all chunks
  that detected the same question number (deduping near-identical
  overlapping regions), and concatenates non-duplicate text - so an answer
  spanning a chunk boundary is fully reconstructed from both chunks' partial
  views rather than either being duplicated or losing a page.

**Page-number safety net.** For any chunk after the first, the vision model
is unreliable about whether a region's `page` means the document's true page
number or just that image's 1-indexed position within the chunk's own
request - confirmed as a real, reproducible failure, not a hypothetical: a
chunk covering true pages `[3, 4]` came back reporting `"page": 1` and
`"page": 2`. Left unchecked, that made every item in the chunk look like it
belonged to an already-processed EARLIER chunk once compared against the
page-ownership map, and it was silently discarded - an entire page's worth
of answers vanishing with no error or warning. `chunking.resolve_absolute_page()`
translates a reported page against the chunk's own known page list
(authoritative, unlike the model's number) before it's used for anything.
This bug is invisible for any document short enough to need only one chunk,
which is exactly why it went unnoticed until a document long enough to need
a second chunk was tested against real files.

## Diagram detection and handling

Both extraction agents can flag `has_diagram: true` on a question or answer
that includes a diagram/figure the model must read (question side) or that
the student drew (answer side) - the vision model already sees the full
page image, this just asks it to report on the diagram instead of silently
describing only the surrounding text.

This mattered for a real, traced bug: `refine_text_region` gives a precise
bounding box by searching for the exact transcribed TEXT in the source
PDF, but it has no concept of "a diagram sits outside that text's own
bounds." Verified against an actual submitted answer sheet (Q8, "draw a
labelled plant cell diagram"): the region shrank from the AI's own looser
guess down to a 0.06-page-height sliver covering only the text sentence,
completely cropping the diagram out of both the highlighted area and the
image later cropped for grading. Fixed by unioning the refined text box
with the AI's own original (wider) guess whenever `has_diagram` is true,
rather than replacing it outright - confirmed against the same real file,
the region now correctly spans the full diagram (checked against the PDF's
own vector-drawing coordinates directly, not just visually). Text-only
answers/questions are unaffected and still get the fully tight refined box.

Grading needed no separate change for this: `grading_agent` already crops
and sends the *actual answer image* (not the transcription) to the vision
model specifically so it can judge diagrams, equations, and tables, not
just prose - fixing the region is what makes that crop actually contain the
diagram's pixels now. Whether the grading model judges a hand-drawn
diagram's *content* accurately (right shapes, right labels) is architecturally
supported but not yet empirically verified against a real graded example -
see "Limitations & assumptions".

## Human-in-the-loop mapping correction

The core principle: **AI proposes, deterministic logic validates, and the
teacher stays in control.** The system never pretends a low-confidence guess
is a confident answer, and every mapping - AI-made or teacher-made - is
visibly labeled which one it is.

- Every `Mapping` carries a `source: "ai" | "teacher"` field. The AI service
  only ever writes `"ai"`; `"teacher"` is set exclusively by the backend's
  correction endpoint, never inferred or guessed elsewhere.
- **`PATCH /api/assessment/:id/mapping`** (`{ questionNumber, answerId }`,
  `answerId: null` for "No Answer") applies a correction with pure,
  deterministic Node.js logic (`mappingService.applyManualCorrection`) - no
  AI call, so it's instant and free. Reassigning an answer that's already
  claimed by a different question automatically resets that question to
  unanswered first (an answer belongs to exactly one question at a time,
  enforced here rather than left to chance), and any now-resolved AI
  validation warning for that specific item is cleaned up so the UI never
  shows a stale complaint about something the teacher just fixed.
- In the UI: a low-confidence question shows its confidence percentage and
  a **Needs Review** badge; a **Review panel** lists every low-confidence
  mapping with a one-click jump; filter pills (`All / Answered / Unanswered
  / Needs Review / Unmatched / Teacher Verified`) narrow the question list.
  Any question (or unmatched answer) has a **Change Answer** /
  **Assign to a question** control that opens a candidate list - reassigning
  an already-claimed answer shows an explicit "already assigned to Question
  X - reassign anyway?" confirmation before it takes effect. A corrected
  mapping immediately shows a **Teacher Verified** badge and the answer
  viewer updates (correct page, correct highlight) with no page reload,
  since it's the same React state the AI-driven selection already used.
- This was verified with a live, scripted browser session (Puppeteer driving
  real Edge against the actual running app, real uploads, real GPT-4o calls,
  real clicks) during development - and that session is what caught two real
  bugs before they shipped: reassigning a previously-unmatched answer was
  leaving behind a phantom `question_number: null` mapping that silently
  inflated the unanswered count, and a resolved validation warning would
  otherwise have kept showing after the fix. Both are now covered by
  permanent regression tests in `backend/tests/mappingService.test.js`.

## Human-in-the-loop grade correction

The same principle applies to grading: an AI-generated score or feedback
comment is a starting point, not a final word, and the teacher can always
override either without re-running AI grading at all.

- **`PATCH /api/assessment/:id/grade`** (`{ questionNumber, score?, feedback? }`
  - either or both) applies the override with deterministic Node.js logic
  (`mappingService.applyGradeCorrection`) - no AI call. The score is clamped
  to `[0, question.max_score]` server-side, exactly like an AI-computed score
  is, so a teacher override gets the same correctness guarantee rather than a
  bare trust of client input. The assessment's total score/percentage is
  recomputed afterward using the identical arithmetic the Python grading
  agent itself uses, so a manual edit stays consistent with the rest of the
  summary.
- A corrected grade is marked `teacher_edited: true` and shows a **Teacher
  Edited** badge in the UI next to the AI Feedback panel - the same visible-
  provenance principle as mapping's `source: "ai" | "teacher"` field, so a
  reviewer can always tell an AI score from a teacher-adjusted one.
- In the UI, the **Edit Grade** control opens a small panel with a numeric
  score field (bounded to the question's max marks) and a feedback textarea,
  pre-filled with the AI's current values - saving updates the score badge,
  feedback panel, and assessment total immediately via the same React state
  the AI grading flow uses, no page reload.

## Highlighting strategy

Bounding boxes are stored and transmitted as **normalized coordinates**
(`0–1`, relative to page width/height), never fixed pixels. The frontend
measures the actual rendered page element (via `ResizeObserver`) and computes:

```js
left   = x * renderedWidth
top    = y * renderedHeight
width  = width * renderedWidth
height = height * renderedHeight
```

This keeps the highlight pixel-accurate at any zoom level or viewport size,
and works identically for PDF pages (rendered with `react-pdf`) and plain
images. Answers spanning multiple pages carry one region per page; the viewer
shows "Region N · Page P" chips so the teacher can jump between them, and
auto-navigates to the first relevant page whenever the selected question
changes.

## Mapping priority (never a silent guess)

| Level | Strategy | Example |
|---|---|---|
| 1 | Exact number match | `11(a)` → `11(a)` |
| 2 | Normalized number match | `Q11 (a)`, `11-A` → `11(a)` |
| 3 | Fuzzy string match | OCR noise, e.g. `ll(a)` |
| 4 | Semantic/content match (model) | number illegible, content clearly answers a specific question |
| 5 | Low-confidence | anything below the confidence bar is still shown, but explicitly labeled `low-confidence` instead of being hidden or presented as certain |

Unanswered questions and unmatched answers are always represented explicitly
in the result — never dropped.

## Running locally

Three terminals:

```bash
# Terminal 1 — frontend
cd frontend
npm install
cp .env.example .env      # set VITE_API_URL if needed
npm run dev               # http://localhost:5173
```

```bash
# Terminal 2 — backend
cd backend
npm install
cp .env.example .env
npm run dev                # http://localhost:5000
```

```bash
# Terminal 3 — agentic AI
cd agentic-ai
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env        # set AI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:5173`. Upload a question paper and an answer sheet
(PDF/PNG/JPG, max 10MB each) and click **Start Mapping**.

## Docker

```bash
cp agentic-ai/.env.example .env   # provide AI_API_KEY at the repo root
docker-compose up --build
```

This builds and runs all three services (`frontend` on :5173, `backend` on
:5000, `agentic-ai` on :8000) wired together via the compose network.

## Environment variables

**frontend/.env**
```
VITE_API_URL=http://localhost:5000/api
```

**backend/.env**
```
PORT=5000
AI_SERVICE_URL=http://localhost:8000
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB=10
CORS_ORIGIN=http://localhost:5173
UPLOAD_TTL_HOURS=6
```

**agentic-ai/.env**
```
PORT=8000
AI_API_KEY=            # never exposed to the frontend or backend logs (OpenRouter key - https://openrouter.ai/keys)
AI_MODEL=openai/gpt-4o
AI_BASE_URL=https://openrouter.ai/api/v1
MAX_IMAGE_DIMENSION=1600
PDF_RENDER_DPI=200
EXTRACTION_CHUNK_SIZE=3      # pages per vision call before a document is split into chunks
EXTRACTION_CHUNK_OVERLAP=1   # pages shared between adjacent chunks
```

## API

**Backend** (`/api`)
```
POST   /upload                        multipart "file" -> { fileId, originalName, size, pageCount }
POST   /assessment/process            { questionFileId, answerFileId } -> full assessment result
GET    /assessment/:id                re-fetch a processed assessment
GET    /assessment/:id/file/:type     stream original file ("question" | "answer")
POST   /assessment/:id/grade          run optional AI grading (uses the stored answer file)
PATCH  /assessment/:id/mapping        { questionNumber, answerId } -> deterministic manual mapping correction
PATCH  /assessment/:id/grade          { questionNumber, score?, feedback? } -> deterministic manual grade correction
DELETE /assessment/:id                delete an assessment and its temp files
GET    /health                        backend + AI-service reachability
```

**Agentic AI**
```
POST /api/process   multipart question_file + answer_file -> AssessmentResult
POST /api/grade      multipart mappings (JSON string) + answer_file? + marking_scheme_file? -> GradingResult
                     (marking_scheme_file is accepted at this layer but never
                     sent by the app - the teacher-facing upload was removed)
GET  /health
```

`/api/grade` is multipart (not a plain JSON body) specifically so the
grading agent can crop and attach the student's actual answer image - text
transcription alone loses diagrams, equations, and tables.

## AI model used

`openai/gpt-4o` (vision-capable, forced function-calling for structured JSON
output on extraction/mapping/rubric/grading calls) via OpenRouter's
OpenAI-compatible endpoint, accessed through the official `openai` Python
SDK (`base_url` pointed at OpenRouter - no separate SDK needed), called with
`temperature=0` throughout for reproducibility. The model id is configurable
via `AI_MODEL` (any OpenRouter-hosted vendor/model id) and `AI_BASE_URL` can
point the same SDK at a different OpenAI-compatible endpoint entirely
without a code change. The provider is fully isolated in `vision_service.py`,
so it can be swapped again without touching any agent.

## File handling & security

- Accepted: PDF, PNG, JPG/JPEG, up to 10MB, validated by extension, MIME
  type, and size on both the backend (Multer) and the AI service.
- Uploaded files are temporary: stored under `backend/uploads/`, released as
  soon as an assessment is deleted, and swept by a TTL-based cleanup job for
  anything abandoned mid-flow.
- The AI service never persists uploaded documents — they're written to a
  temp path only for the duration of the request and removed in a `finally`
  block.
- `AI_API_KEY` only ever lives in `agentic-ai/.env` / the AI service's
  process environment. It is never sent to, or reachable from, the frontend.
- `.env` files are gitignored; only `.env.example` files are committed.

## Deployment

- **Frontend** → static host (Vercel, Render Static Site, etc.) — build with
  `npm run build`, publish `dist/`, set `VITE_API_URL` to
  `<deployed-backend-url>/api` (with the `/api` suffix - a real deploy hit a
  silent `404 Route not found` from missing it). Vite bakes env vars in at
  **build time**, so this must be set before the build runs, not after -
  changing it later needs a fresh build, not just a redeploy of the same
  artifact.
- **Backend** → Render / Railway (Node) — set `AI_SERVICE_URL` to the
  deployed agentic-ai URL and `CORS_ORIGIN` to the exact deployed frontend
  origin (no trailing slash).
- **Agentic AI** → Render / Railway (Python) — set `AI_API_KEY` / `AI_MODEL`
  / `AI_BASE_URL`.

Each service can be deployed and scaled independently; the only coupling is
the two HTTP URLs (`AI_SERVICE_URL` on the backend, `VITE_API_URL` on the
frontend).

**Render-specific notes from an actual deployment**, since these cost real
debugging time and aren't obvious from the platform's own docs:

- If the repo lives in a subdirectory relative to the git root, Render's
  **Root Directory** field needs the full path from the repo root (e.g.
  `ai-assessment-mapper/agentic-ai`), not just the service folder name.
- PyMuPDF's `requirements.txt` pin only ships prebuilt wheels for a bounded
  Python version range. Render's default Python is often newer than that
  range, which makes `pip install` fall back to compiling PyMuPDF's bundled
  MuPDF C++ source from scratch - and that source fails to compile against
  modern CPython headers. Fix: set the `PYTHON_VERSION` environment
  variable explicitly (e.g. `3.11.9`) on the agentic-ai service. A
  `runtime.txt` at the service root is the documented alternative, but it's
  only reliably picked up when Render's Root Directory *is* the repo root -
  when the service lives in a subdirectory, the environment variable is the
  one that actually works.
- Grading and long-document extraction can legitimately take several
  minutes (see "Chunked document processing" - each chunk is its own
  sequential vision call). Both the backend's axios timeout to the AI
  service and the frontend's own request timeout are set to 10 minutes for
  exactly this reason; shortening either will abort a request that's still
  legitimately working, not stuck.
- Render's free tier spins down a service after ~15 minutes of inactivity,
  and the first request afterward pays a 30-90s cold-start penalty - it can
  even return a `502` to that very first waking request while the container
  finishes booting, which looks like a crash but isn't. A free external
  cron ping (e.g. cron-job.org hitting each service's `/health` every 5
  minutes) keeps both warm; a paid instance is the more robust fix if
  uptime matters more than cost.

## Testing

```bash
# agentic-ai: Python test suite + evaluation dataset
cd agentic-ai
venv\Scripts\activate
pip install -r requirements.txt   # includes pytest
pytest -v                          # 73 tests, ~10 seconds, no API key needed
python test-data/evaluate.py       # 21-case mapping-accuracy eval against known-expected fixtures

# backend: Node's built-in test runner, no extra dependency
cd backend
npm test                           # 18 tests, ~1 second
```

The pytest suite (`agentic-ai/tests/`) covers normalization, deterministic
ordering, bounding-box validation, chunking/merge logic (including the
chunk-relative page-number safety net), the MCQ-vs-sub-part merge, the
diagram-region union for both questions and answers, EXIF image-rotation
correction, the full mapping priority ladder (with Level 4 mocked), and
grading (rubric rescaling, criterion clamping, mismatch handling) -
entirely offline and deterministic, so it's genuinely repeatable in CI
without incurring API cost or flakiness from live model calls. It also
carries explicit regression tests for real bugs found and fixed during
development (e.g. `Q5 continued` normalizing differently from `Q5`; `7(4)`
failing to fuzzy-match `7(a)`; a chunk covering true pages `[3, 4]`
reporting `"page": 1`/`"page": 2` and silently losing every answer on the
later page; a diagram getting cropped out of an answer's highlighted
region).

`test-data/evaluate.py` runs the real mapping/validation logic against 21
hand-labeled fixtures (`test-data/case_*/`, generated by
`test-data/generate_cases.py`) with known-correct expected mappings, covering
every scenario in the test plan - normal/out-of-order answers, sub-parts
(`11(a)`), nested sub-parts (`11(a)(i)`), unanswered/unmatched/duplicate
answers, fuzzy and similar-looking numbers, multi-page and chunk-boundary
answers, continuation pages, poor handwriting, blank pages, stray notes, and
missing/ambiguous question numbers (the last two via a mocked semantic
response, so the whole suite still needs no API key). It reports mapping
accuracy, sub-question accuracy, unmatched/unanswered detection accuracy,
and multi-page mapping accuracy - all measured, none fabricated. Last run:
**100% on every metric across all 21 cases / 46 questions.**

The backend's `npm test` (`backend/tests/`, Node's built-in `node:test` - no
new dependency) covers the deterministic manual-correction logic for both
mappings (`applyManualCorrection`: reassignment correctly resets the
previous holder, "No Answer" and unmatched-answer assignment, unknown-id
error handling) and grades (`applyGradeCorrection`: score clamped to
`[0, max_score]`, feedback-only vs score-only vs both, the assessment total
recomputed deterministically afterward), plus a real regression test using
an actual PyMuPDF-generated PDF fixture for the xref-stream upload bug.

None of this tests what the vision model itself sees or interprets - a few
tests mock its response to exercise the deterministic logic around it (page
remapping, MCQ merging, diagram-region unioning), but real extraction
quality was verified manually against the live API during development,
including against actual submitted documents when a reported bug needed
reproducing against real content rather than a synthetic stand-in.
Interactive frontend flows are covered only by a live manual browser-driven
pass performed during development (see "Limitations & assumptions").

## Limitations & assumptions

- Grading is optional and only ever runs on explicit teacher action — it is
  never required for the core extraction/mapping/highlighting flow.
- Extraction quality depends on scan/photo quality and the underlying vision
  model; the validation agent surfaces warnings rather than failing silently,
  but very poor scans can still produce low-confidence or missing results by
  design (this is treated as a graceful degradation, not a bug).
- The in-memory assessment/file stores are process-local, which is sufficient
  for a single backend instance; horizontally scaling the backend would need
  a shared store (Redis/DB) instead of the current `Map`.
- Semantic (Level 4) matching costs one extra model call per still-unmatched
  answer, so pathological documents with many unmatched answers take longer
  to map — this is intentional (a real match beats a fast wrong one).
- Chunking bounds confusion between far-apart questions, but a single answer
  that spans more physical pages than `EXTRACTION_CHUNK_OVERLAP` allows,
  landing awkwardly across a chunk boundary, could still be reconstructed
  imperfectly (in practice this needs both a very long single-question
  answer and unlucky page alignment — increasing the overlap setting is the
  mitigation for exam formats with long essay-style answers).
- No embeddings, vector database, or RAG are used anywhere. This was a
  deliberate choice, not an oversight: an early keyword-overlap heuristic
  (considered as a lighter-weight alternative) was tested and demonstrably
  produced false positives on legitimate terse numeric answers, and was
  removed rather than shipped — see the mismatch-detection design above,
  which uses the grading model's own contextual judgement instead.
- Numerical/arithmetic verification is not independently checked by
  deterministic code — the grading model evaluates method and correctness
  itself (aided by seeing the actual answer image, not just a transcription
  that can garble equations), but it can still make an arithmetic judgement
  error, as any single ungrounded evaluation can. A dedicated symbolic
  arithmetic checker was considered but not built, since a reliable general
  version was out of scope for this project's size.
- Grading can evaluate a diagram in principle (see "Diagram detection and
  handling") - the crop sent to the model now correctly includes the
  diagram's pixels - but how *accurately* the model judges a hand-drawn
  diagram's content (right shapes, right labels) is not yet verified
  against a real graded example, only assumed from it being a general-
  purpose vision model. Treat diagram grading as unverified until checked.
- Page preprocessing before sending images to the model handles DPI-
  controlled rendering and EXIF-based rotation correction (a photographed
  answer sheet held sideways/upside-down, per its EXIF orientation tag, is
  corrected before being sent to the model — see `load_document_pages` in
  `pdf_service.py`, tested in `tests/test_image_orientation.py`). General
  deskew (for a crookedly-photographed page with no EXIF tag to rely on) and
  contrast normalization are still not implemented, since a reliable version
  needed real image-processing/CV work whose benefit couldn't be verified
  without a corpus of actually-skewed scans to test against.
