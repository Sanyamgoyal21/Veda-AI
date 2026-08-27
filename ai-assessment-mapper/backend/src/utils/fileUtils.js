const fs = require("fs");
const path = require("path");
const pdfParse = require("pdf-parse");

const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg"]);

// Crude fallback page counter: counts page-object declarations directly in
// the raw PDF bytes. Used only when pdf-parse's bundled (old) pdf.js can't
// parse the file - notably, PDFs written with modern cross-reference
// streams (e.g. PyMuPDF's default output) trip up that old parser with a
// "bad XRef entry" error even though they're perfectly valid PDFs. This
// never blocks an upload just because we can't get an exact page count -
// the actual document processing in the AI service uses PyMuPDF directly
// and is unaffected either way.
function countPageObjects(buffer) {
  const matches = buffer.toString("latin1").match(/\/Type\s*\/Page(?!s)/g);
  return matches ? matches.length : 0;
}

async function getPageCount(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (IMAGE_EXTENSIONS.has(ext)) {
    return 1;
  }
  const buffer = fs.readFileSync(filePath);
  try {
    const data = await pdfParse(buffer);
    return data.numpages;
  } catch (err) {
    console.warn(`pdf-parse could not read ${filePath}, using fallback page count: ${err.message}`);
    const fallbackCount = countPageObjects(buffer);
    return fallbackCount > 0 ? fallbackCount : 1;
  }
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
