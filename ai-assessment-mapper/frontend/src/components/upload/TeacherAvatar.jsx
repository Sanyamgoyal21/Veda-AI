import { GraduationCap } from "lucide-react";

const DOT_POSITIONS = [
  "-top-1 left-6",
  "top-4 -right-1",
  "bottom-2 -right-2",
  "-bottom-1 left-8",
];

export default function TeacherAvatar() {
  return (
    <div className="relative w-28 h-28 mx-auto mb-8">
      <div className="absolute inset-[-14px] rounded-full bg-brand-orangeSoft" />
      <div className="absolute inset-[-6px] rounded-full bg-brand-orangeLight" />
      <div className="relative w-28 h-28 rounded-full bg-white border-4 border-white shadow-card flex items-center justify-center overflow-hidden">
        <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center">
          <GraduationCap size={40} className="text-white" />
        </div>
      </div>
      {DOT_POSITIONS.map((pos, i) => (
        <span
          key={i}
          className={`absolute ${pos} w-3.5 h-3.5 rounded-full bg-brand-orange border-2 border-white`}
        />
      ))}
    </div>
  );
}
