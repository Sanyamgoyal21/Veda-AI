const { ApiError } = require("../utils/validation");
const fileService = require("../services/fileService");

async function uploadFile(req, res, next) {
  try {
    if (!req.file) {
      throw new ApiError(400, "No file was uploaded. Expected multipart field 'file'.");
    }
    const meta = await fileService.registerUpload(req.file);
    res.status(201).json(meta);
  } catch (err) {
    next(err);
  }
}

module.exports = { uploadFile };
