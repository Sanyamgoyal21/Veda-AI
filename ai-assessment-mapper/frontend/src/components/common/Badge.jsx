import { classNames } from "../../utils/formatters";

export default function Badge({ children, className }) {
  return (
    <span
      className={classNames(
        "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold",
        className
      )}
    >
      {children}
    </span>
  );
}
