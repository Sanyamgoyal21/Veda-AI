/**
 * Tracks uploaded temp files by an opaque fileId so the two-step
 * "upload -> then process" flow doesn't require re-uploading bytes.
 * In-memory only: files live on disk under uploads/ and are purged either
 * when their assessment is deleted or after UPLOAD_TTL_HOURS.
 */
const path = require("path");
const { v4: uuidv4 } = require("uuid");
const { getPageCount, mimeForExtension, safeUnlink } = require("../utils/fileUtils");
const { ApiError } = require("../utils/validation");
const config = require("../config/config");

const files = new Map(); // fileId -> { path, originalName, size, mimeType, pageCount, createdAt }

async function registerUpload(multerFile) {
  const fileId = uuidv4();
  const pageCount = await getPageCount(multerFile.path);

  files.set(fileId, {
    path: multerFile.path,
    originalName: multerFile.originalname,
    size: multerFile.size,
    mimeType: mimeForExtension(path.extname(multerFile.originalname)),
    pageCount,
    createdAt: Date.now(),
  });

  return { fileId, originalName: multerFile.originalname, size: multerFile.size, pageCount };
}

function getFile(fileId) {
  const file = files.get(fileId);
  if (!file) {
    throw new ApiError(404, `Unknown fileId: ${fileId}`);
  }
  return file;
}

function releaseFile(fileId) {
  const file = files.get(fileId);
  if (file) {
    safeUnlink(file.path);
    files.delete(fileId);
  }
}

function purgeExpired() {
  const ttlMs = config.uploadTtlHours * 60 * 60 * 1000;
  const now = Date.now();
  for (const [fileId, file] of files.entries()) {
    if (now - file.createdAt > ttlMs) {
      releaseFile(fileId);
    }
  }
}

function toMeta(file) {
  return { mimeType: file.mimeType, pageCount: file.pageCount, originalName: file.originalName };
}

function getFileMetaPair(questionFileId, answerFileId) {
  return {
    question: toMeta(getFile(questionFileId)),
    answer: toMeta(getFile(answerFileId)),
  };
}

module.exports = { registerUpload, getFile, releaseFile, purgeExpired, getFileMetaPair };
