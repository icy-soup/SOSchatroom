import { CHARACTERS, getCharacter } from "../characters";

interface SidebarProps {
  currentCharacter: string | null;
  onSelect: (name: string) => void;
}

export default function Sidebar({ currentCharacter, onSelect }: SidebarProps) {
  return (
    <aside className="w-44 bg-white/50 backdrop-blur-sm border-r border-black/5 flex flex-col shrink-0">
      <div className="px-3 py-2.5 text-xs text-black/30 font-medium border-b border-black/5">
        选择角色
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {CHARACTERS.map((c) => {
          const isActive = currentCharacter === c.name;
          return (
            <div
              key={c.name}
              onClick={() => onSelect(c.name)}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-md text-sm cursor-pointer
                transition-all duration-150
                ${isActive
                  ? "bg-black/6 border-l-3 text-black/80"
                  : "hover:bg-black/4 text-black/60 border-l-3 border-transparent"
                }
              `}
              style={isActive ? { borderLeftColor: c.color } : undefined}
            >
              <span>{c.emoji}</span>
              <span>{c.name}</span>
            </div>
          );
        })}
      </div>

      {currentCharacter && (
        <div className="px-3 py-2.5 border-t border-black/5">
          <div className="text-[10px] text-black/30 mb-0.5">当前扮演</div>
          <div className="flex items-center gap-1.5">
            <span>{getCharacter(currentCharacter).emoji}</span>
            <span className="text-sm font-medium text-[#2c2c2c]">
              {currentCharacter}
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
