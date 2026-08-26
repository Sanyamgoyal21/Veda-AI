const path = require("path");
require("dotenv").config();

const config = {
  port: parseInt(process.env.PORT, 10) || 5000,
  aiServiceUrl: process.env.AI_SERVICE_URL || "http://localhost:8000",
  uploadDir: path.resolve(__dirname, "..", "..", process.env.UPLOAD_DIR || "uploads"),
  maxFileSizeBytes: (parseInt(process.env.MAX_FILE_SIZE_MB, 10) || 10) * 1024 * 1024,
  corsOrigin: process.env.CORS_ORIGIN || "http://localhost:5173",
  uploadTtlHours: parseInt(process.env.UPLOAD_TTL_HOURS, 10) || 6,
  allowedExtensions: [".pdf", ".png", ".jpg", ".jpeg"],
  allowedMimeTypes: ["application/pdf", "image/png", "image/jpeg"],
};

module.exports = config;
