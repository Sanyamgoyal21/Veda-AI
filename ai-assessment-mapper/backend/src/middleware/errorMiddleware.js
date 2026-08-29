const multer = require("multer");
const { ApiError } = require("../utils/validation");

function notFoundHandler(req, res) {
  res.status(404).json({ error: `Route not found: ${req.method} ${req.originalUrl}` });
}

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  if (err instanceof multer.MulterError) {
    const message =
      err.code === "LIMIT_FILE_SIZE"
        ? "File exceeds the maximum allowed size of 10MB"
        : err.message;
    return res.status(400).json({ error: message });
  }

  if (err instanceof ApiError) {
    return res.status(err.statusCode).json({ error: err.message });
  }

  if (err.isAxiosError) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail || err.response?.data?.error;

    if (status && status < 500) {
      return res.status(status).json({ error: detail || "The AI service rejected the request" });
    }
    if (err.code === "ECONNABORTED") {
      return res.status(504).json({
        error: "Grading is taking longer than expected for this many questions. Please try again.",
      });
    }
    if (err.code === "ECONNREFUSED") {
      return res.status(503).json({ error: "The AI service is unavailable. Please retry shortly." });
    }
    console.error("AI service error:", detail || err.message);
    return res.status(502).json({ error: "The AI service failed to process the request" });
  }

  console.error("Unhandled error:", err);
  return res.status(500).json({ error: "Something went wrong. Please try again." });
}

module.exports = { notFoundHandler, errorHandler };
