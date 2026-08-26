const app = require("./app");
const config = require("./config/config");
const fileService = require("./services/fileService");

const server = app.listen(config.port, () => {
  console.log(`Backend API listening on http://localhost:${config.port}`);
  console.log(`Forwarding AI requests to ${config.aiServiceUrl}`);
});

// Periodically purge orphaned temp uploads that never made it into a
// processed assessment (e.g. the user uploaded but abandoned the flow).
const cleanupInterval = setInterval(() => fileService.purgeExpired(), 60 * 60 * 1000);

process.on("SIGTERM", () => {
  clearInterval(cleanupInterval);
  server.close(() => process.exit(0));
});

module.exports = server;
