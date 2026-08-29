/**
 * Regression test: pdf-parse's bundled (old) pdf.js throws "bad XRef entry"
 * on PDFs written with modern cross-reference streams - notably PyMuPDF's
 * default output, which every PDF the agentic-ai service or a teacher's own
 * tools might produce. getPageCount must never let that exception bubble up
 * and block an upload; it should fall back to a best-effort count instead.
 *
 * tests/fixtures/xref_stream_sample.pdf is a real 2-page PDF generated with
 * PyMuPDF, confirmed to trigger pdf-parse's bug directly (not simulated).
 */
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { getPageCount } = require("../src/utils/fileUtils");

const FIXTURE = path.join(__dirname, "fixtures", "xref_stream_sample.pdf");

test("getPageCount does not throw on a PDF that trips up pdf-parse's bundled parser", async () => {
  const count = await getPageCount(FIXTURE);
  assert.equal(typeof count, "number");
  assert.ok(count >= 1, "must return at least 1 rather than throwing or returning 0");
});

test("getPageCount's fallback finds the correct page count for the xref-stream fixture", async () => {
  // The fixture has exactly 2 pages - the regex fallback should find both.
  const count = await getPageCount(FIXTURE);
  assert.equal(count, 2);
});
