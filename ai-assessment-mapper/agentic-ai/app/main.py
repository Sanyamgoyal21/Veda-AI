import json
import logging
import os
import tempfile
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

load_dotenv()

from app.services.vision_service import VisionServiceError  # noqa: E402
from app.workflows import assessment_workflow  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentic-ai")

app = FastAPI(title="AI Assessment Mapper - Agentic AI Service", version="1.0.0")

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB, mirrors the frontend/backend limit


def _validate_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext or 'unknown'}")
    return ext


async def _save_upload(file: UploadFile, ext: str) -> str:
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 10MB size limit")
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{ext}")
    with open(tmp_path, "wb") as f:
        f.write(contents)
    return tmp_path


@app.get("/health")
def health():
    return {"status": "ok", "service": "agentic-ai"}


@app.post("/api/process")
async def process(
    question_file: UploadFile = File(...),
    answer_file: UploadFile = File(...),
):
    q_ext = _validate_upload(question_file)
    a_ext = _validate_upload(answer_file)

    q_path = a_path = None
    try:
        q_path = await _save_upload(question_file, q_ext)
        a_path = await _save_upload(answer_file, a_ext)

        result = assessment_workflow.process_assessment(q_path, a_path)
        return JSONResponse(content=result.model_dump())

    except ValueError as exc:
        logger.warning("Bad document: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VisionServiceError as exc:
        logger.error("Vision provider failure: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        for path in (q_path, a_path):
            if path and os.path.exists(path):
                os.remove(path)


@app.post("/api/grade")
async def grade(
    mappings: str = Form(...),
    answer_file: UploadFile | None = File(None),
    marking_scheme_file: UploadFile | None = File(None),
):
    try:
        mappings_payload = json.loads(mappings)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="`mappings` must be valid JSON") from exc
    if not mappings_payload:
        raise HTTPException(status_code=400, detail="`mappings` is required")

    answer_path = marking_scheme_path = None
    try:
        if answer_file is not None:
            ext = _validate_upload(answer_file)
            answer_path = await _save_upload(answer_file, ext)
        if marking_scheme_file is not None:
            ext = _validate_upload(marking_scheme_file)
            marking_scheme_path = await _save_upload(marking_scheme_file, ext)

        result = assessment_workflow.grade_assessment(
            mappings_payload,
            answer_file_path=answer_path,
            marking_scheme_file_path=marking_scheme_path,
        )
        return JSONResponse(content=result)
    except VisionServiceError as exc:
        logger.error("Vision provider failure during grading: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        for path in (answer_path, marking_scheme_path):
            if path and os.path.exists(path):
                os.remove(path)
