const express = require("express");
const cors = require("cors");
const morgan = require("morgan");

const config = require("./config/config");
const uploadRoutes = require("./routes/uploadRoutes");
const assessmentRoutes = require("./routes/assessmentRoutes");
const gradingRoutes = require("./routes/gradingRoutes");
const aiService = require("./services/aiService");
const { notFoundHandler, errorHandler } = require("./middleware/errorMiddleware");

const app = express();

app.use(cors({ origin: config.corsOrigin }));
app.use(express.json());
app.use(morgan("dev"));

app.get("/api/health", async (req, res) => {
  let aiServiceStatus = "unreachable";
  try {
    await aiService.checkHealth();
    aiServiceStatus = "ok";
  } catch {
    aiServiceStatus = "unreachable";
  }
  res.json({ status: "ok", service: "backend", aiService: aiServiceStatus });
});

app.use("/api/upload", uploadRoutes);
app.use("/api/assessment", assessmentRoutes);
app.use("/api/assessment", gradingRoutes);

app.use(notFoundHandler);
app.use(errorHandler);

module.exports = app;
