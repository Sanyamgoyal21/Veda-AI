export default function Spinner({ size = 18, className = "" }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-gray-200 border-t-brand-orange ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
