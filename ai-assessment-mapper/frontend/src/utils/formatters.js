export function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "";
  if (bytes < 1024) return `${bytes}B`;
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(mb >= 10 ? 0 : 1)}MB`;
  const kb = bytes / 1024;
  return `${kb.toFixed(0)}KB`;
}

export function formatPageLabel(count) {
  return count === 1 ? "1 Page" : `${count} Pages`;
}

export function classNames(...values) {
  return values.filter(Boolean).join(" ");
}
