import { CHARACTERS } from "../characters";

interface CharacterSelectorBarProps {
  currentCharacter: string | null;
  onSelect: (name: string) => void;
}

export default function CharacterSelectorBar({ currentCharacter, onSelect }: CharacterSelectorBarProps) {
  return (
    <div className="px-4 py-3 border-t border-black/5 bg-white/40">
      <div className="text-[11px] text-black/30 mb-2 text-center font-medium">
        选择角色开始对话
      </div>
      <div className="flex items-center justify-center gap-2">
        {CHARACTERS.map((c) => {
          const isActive = currentCharacter === c.name;
          return (
            <button
              key={c.name}
              onClick={() => onSelect(c.name)}
              className={`
                flex flex-col items-center gap-1 px-3 py-2 rounded-xl cursor-pointer
                transition-all duration-150 min-w-[60px]
                ${isActive
                  ? "bg-purple-100 ring-2 ring-purple-300 scale-105"
                  : "hover:bg-black/5 active:scale-95"
                }
              `}
            >
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-base"
                style={{ background: `${c.color}18` }}
              >
                {c.emoji}
              </div>
              <span
                className="text-[11px] font-medium truncate max-w-[56px]"
                style={{ color: isActive ? c.color : undefined }}
              >
                {c.name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
