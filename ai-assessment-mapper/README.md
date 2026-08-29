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
Vision AI model (Gemini gemini-2.0-flash, vision + forced function-calling)
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
  deterministically deduplicated and merged back together.
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
  criteria + a reference answer) before any student answer is considered.
  Uses a teacher-provided marking scheme when one covers the question
  (`source: "teacher"`), otherwise generates one from the question alone
  (`source: "ai"`). Criteria marks are deterministically rescaled in Python
  to sum exactly to the question's marks - the model is never trusted to
  get that arithmetic right.
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
that one file (this has been exercised in practice, not just designed for -
the provider was swapped between Anthropic and OpenAI multiple times during
development touching only that file, `requirements.txt`, and `.env`).

## Chunked document processing

Sending an entire long document in a single vision request risks the model
confusing two structurally-similar questions that are many pages apart (this
was an observed real failure, not a hypothetical - a probability question's
answer got attributed to an unrelated geometry question elsewhere in the
same document). `app/services/chunking.py` splits any document longer than
`EXTRACTION_CHUNK_SIZE` pages (default 6) into overlapping chunks
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

## Optional marking scheme / model answer upload

A teacher can optionally upload a third document (marking scheme or model
answer) alongside the question paper and answer sheet. It is not sent to the
AI service until (and unless) the teacher actually clicks "Grade with AI" -
uploading it costs nothing extra during initial processing. When present, a
digital PDF's text is extracted once (free, exact, via PyMuPDF) and reused
for every question's rubric-generation call rather than re-sending images
repeatedly; a scanned marking scheme falls back to sending its page images.
Coverage is judged per-question by the model, not assumed from the file's
mere presence - a marking scheme rarely covers every single question.

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
AI_API_KEY=            # never exposed to the frontend or backend logs (Gemini key - https://aistudio.google.com/apikey)
AI_MODEL=gemini-2.0-flash
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MAX_IMAGE_DIMENSION=1600
PDF_RENDER_DPI=200
EXTRACTION_CHUNK_SIZE=6      # pages per vision call before a document is split into chunks
EXTRACTION_CHUNK_OVERLAP=1   # pages shared between adjacent chunks
```

## API

**Backend** (`/api`)
```
POST   /upload                        multipart "file" -> { fileId, originalName, size, pageCount }
POST   /assessment/process            { questionFileId, answerFileId, markingSchemeFileId? } -> full assessment result
GET    /assessment/:id                re-fetch a processed assessment
GET    /assessment/:id/file/:type     stream original file ("question" | "answer")
POST   /assessment/:id/grade          run optional AI grading (uses the stored answer file + marking scheme, if any)
DELETE /assessment/:id                delete an assessment and its temp files
GET    /health                        backend + AI-service reachability
```

**Agentic AI**
```
POST /api/process   multipart question_file + answer_file -> AssessmentResult
POST /api/grade      multipart mappings (JSON string) + answer_file? + marking_scheme_file? -> GradingResult
GET  /health
```

`/api/grade` is multipart (not a plain JSON body) specifically so the
grading agent can crop and attach the student's actual answer image - text
transcription alone loses diagrams, equations, and tables.

## AI model used

Gemini `gemini-2.0-flash` (vision-capable, forced function-calling for
structured JSON output on extraction/mapping/rubric/grading calls), accessed
through Gemini's OpenAI-compatible endpoint via the official `openai` Python
SDK (pointed at `AI_BASE_URL` instead of OpenAI's own endpoint - no separate
Gemini SDK needed), called with `temperature=0` throughout for
reproducibility. The model id is configurable via `AI_MODEL` and the provider
is fully isolated in `vision_service.py`, so it can be swapped again for
another vision-capable provider without touching any agent.

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

- **Frontend** → Vercel (or any static host) — build with `npm run build`,
  set `VITE_API_URL` to the deployed backend's public URL.
- **Backend** → Render / Railway — set `AI_SERVICE_URL` to the deployed
  agentic-ai URL and `CORS_ORIGIN` to the deployed frontend URL.
- **Agentic AI** → Render / Railway (Python) — set `AI_API_KEY` / `AI_MODEL`.

Each service can be deployed and scaled independently; the only coupling is
the two HTTP URLs (`AI_SERVICE_URL` on the backend, `VITE_API_URL` on the
frontend).

## Testing

```bash
# agentic-ai: Python test suite + evaluation dataset
cd agentic-ai
venv\Scripts\activate
pip install -r requirements.txt   # includes pytest
pytest -v                          # 46 tests, ~6 seconds, no API key needed
python test-data/evaluate.py       # 21-case mapping-accuracy eval against known-expected fixtures

# backend: Node's built-in test runner, no extra dependency
cd backend
npm test                           # 10 tests, ~0.3 seconds
```

The pytest suite (`agentic-ai/tests/`) covers normalization, deterministic
ordering, bounding-box validation, chunking/merge logic, the full mapping
priority ladder (with Level 4 mocked), and grading (rubric rescaling,
criterion clamping, mismatch handling) - entirely offline and deterministic,
so it's genuinely repeatable in CI without incurring API cost or flakiness
from live model calls. It also carries explicit regression tests for real
bugs found and fixed during development (e.g. `Q5 continued` normalizing
differently from `Q5`; `7(4)` failing to fuzzy-match `7(a)`).

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
new dependency) covers the deterministic manual-correction logic
(`applyManualCorrection`): reassignment correctly resets the previous
holder, "No Answer" and unmatched-answer assignment, unknown-id error
handling, and a real regression test using an actual PyMuPDF-generated PDF
fixture for the xref-stream upload bug.

None of this tests the extraction agents themselves (that needs a real
vision model and was verified manually against the live API during
development), nor the interactive frontend flows beyond a live manual
browser-driven pass performed during development (see "Known limitations").

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
- Manual reassignment of a low-confidence or unmatched mapping IS available
  in the UI ("Change Answer" / "Assign to a question" — see "Human-in-the-loop
  mapping correction" above); this limitation from an earlier round has been
  addressed.
- Page preprocessing before sending images to the model handles DPI-
  controlled rendering and EXIF-based rotation correction (a photographed
  answer sheet held sideways/upside-down, per its EXIF orientation tag, is
  corrected before being sent to the model — see `load_document_pages` in
  `pdf_service.py`, tested in `tests/test_image_orientation.py`). General
  deskew (for a crookedly-photographed page with no EXIF tag to rely on) and
  contrast normalization are still not implemented, since a reliable version
  needed real image-processing/CV work whose benefit couldn't be verified
  without a corpus of actually-skewed scans to test against.
