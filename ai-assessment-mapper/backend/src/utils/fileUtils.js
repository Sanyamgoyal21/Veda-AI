const fs = require("fs");
const path = require("path");
const pdfParse = require("pdf-parse");

const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg"]);

async function getPageCount(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (IMAGE_EXTENSIONS.has(ext)) {
    return 1;
  }
  const buffer = fs.readFileSync(filePath);
  const data = await pdfParse(buffer);
  return data.numpages;
}

function mimeForExtension(ext) {
  switch (ext.toLowerCase()) {
    case ".pdf":
      return "application/pdf";
    case ".png":
      return "image/png";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    default:
      return "application/octet-stream";
  }
}

function safeUnlink(filePath) {
  if (filePath && fs.existsSync(filePath)) {
    fs.unlink(filePath, () => {});
  }
}

module.exports = { getPageCount, mimeForExtension, safeUnlink };
