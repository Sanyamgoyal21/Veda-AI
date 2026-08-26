import { classNames } from "../../utils/formatters";

const VARIANTS = {
  primary: "bg-ink text-white hover:bg-black disabled:bg-gray-200 disabled:text-gray-400",
  secondary: "bg-gray-100 text-ink hover:bg-gray-200",
  outline: "border border-gray-200 text-ink hover:bg-gray-50",
  danger: "bg-red-50 text-red-600 hover:bg-red-100",
};

export default function Button({
  children,
  variant = "primary",
  className,
  disabled,
  ...props
}) {
  return (
    <button
      disabled={disabled}
      className={classNames(
        "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed",
        VARIANTS[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
