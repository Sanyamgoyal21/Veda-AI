/**
 * Converts a normalized (0-1) bounding box into pixel coordinates relative
 * to the currently rendered page size. Never use fixed pixel values here -
 * renderedWidth/renderedHeight change whenever the viewer is zoomed or
 * resized, and normalized coordinates stay valid regardless.
 */
export function normalizedToPixelRect(region, renderedWidth, renderedHeight) {
  return {
    left: region.x * renderedWidth,
    top: region.y * renderedHeight,
    width: region.width * renderedWidth,
    height: region.height * renderedHeight,
  };
}

/** Returns the sorted list of unique page numbers a set of regions spans. */
export function pagesFromRegions(regions) {
  return [...new Set(regions.map((r) => r.page))].sort((a, b) => a - b);
}
