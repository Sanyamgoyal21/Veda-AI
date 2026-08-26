const path = require("path");
const config = require("../config/config");

class ApiError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.statusCode = statusCode;
  }
}

function assertAllowedFile(file) {
  const ext = path.extname(file.originalname).toLowerCase();
  if (!config.allowedExtensions.includes(ext)) {
    throw new ApiError(400, `Unsupported file extension "${ext}". Allowed: PDF, PNG, JPG, JPEG`);
  }
  if (!config.allowedMimeTypes.includes(file.mimetype)) {
    throw new ApiError(400, `Unsupported file type "${file.mimetype}"`);
  }
  if (file.size > config.maxFileSizeBytes) {
    throw new ApiError(400, "File exceeds the maximum allowed size of 10MB");
  }
}

function requireFields(body, fields) {
  const missing = fields.filter((field) => !body[field]);
  if (missing.length > 0) {
    throw new ApiError(400, `Missing required field(s): ${missing.join(", ")}`);
  }
}

module.exports = { ApiError, assertAllowedFile, requireFields };
