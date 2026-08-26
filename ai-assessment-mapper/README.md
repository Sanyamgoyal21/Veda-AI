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
Vision AI model (Anthropic Claude, vision + tool-use)
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
  extracts every question (including sub-parts like `11(a)`), preserving
  printed numbering, order, and page.
- **answer_extraction_agent** — reads the rendered answer-sheet pages and
  extracts every handwritten answer with a confidence score and one or more
  normalized bounding-box regions (multi-page answers get one region per page).
- **mapping_agent** — matches answers to questions through a strict priority
  ladder: exact number → normalized number (`Q11(a)`, `11 (a)`, `11-A` all
  resolve the same) → fuzzy string match → semantic/content match via the
  model (last resort) → otherwise the mapping is kept but explicitly labeled
  `low-confidence`. A mapping is never silently presented as confident.
- **validation_agent** — flags duplicate/missing questions, invalid pages,
  degenerate bounding boxes, unmatched answers, unanswered questions, and
  low-confidence mappings.
- **grading_agent** (optional, P2) — only runs when the teacher clicks
  "Grade with AI"; scores and gives feedback per mapped question.

All prompts live in `agentic-ai/app/prompts/`, one file per agent — agents
never inline giant prompt strings. All AI provider calls go through
`agentic-ai/app/services/vision_service.py`; swapping providers means editing
that one file.

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
AI_API_KEY=            # never exposed to the frontend or backend logs
AI_MODEL=claude-sonnet-5
MAX_IMAGE_DIMENSION=1600
PDF_RENDER_DPI=200
```

## API

**Backend** (`/api`)
```
POST   /upload                        multipart "file" -> { fileId, originalName, size, pageCount }
POST   /assessment/process            { questionFileId, answerFileId } -> full assessment result
GET    /assessment/:id                re-fetch a processed assessment
GET    /assessment/:id/file/:type     stream original file ("question" | "answer")
POST   /assessment/:id/grade          run optional AI grading
DELETE /assessment/:id                delete an assessment and its temp files
GET    /health                        backend + AI-service reachability
```

**Agentic AI**
```
POST /api/process   multipart question_file + answer_file -> AssessmentResult
POST /api/grade      { mappings } -> GradingResult
GET  /health
```

## AI model used

Anthropic Claude (vision-capable, tool-use forced for structured JSON output)
via the official `anthropic` Python SDK. The model id is configurable via
`AI_MODEL` and the provider is fully isolated in `vision_service.py`, so it
can be swapped for another vision-capable provider without touching any agent.

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
