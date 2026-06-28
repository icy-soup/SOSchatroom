import { type PanelView } from "../types";

interface IconBarProps {
  activeView: PanelView | null;
  onSelect: (view: PanelView) => void;
  onSettings: () => void;
  darkMode: boolean;
  onToggleDark: () => void;
}

const ICONS: { view: PanelView; icon: string; label: string }[] = [
  { view: "chat", icon: "💬", label: "聊天" },
  { view: "contacts", icon: "👥", label: "联系人" },
  { view: "tools", icon: "🛠", label: "工具" },
  { view: "market", icon: "🏪", label: "市场" },
];

export default function IconBar({ activeView, onSelect, onSettings, darkMode, onToggleDark }: IconBarProps) {
  return (
    <div className="w-[54px] bg-[#202123] flex flex-col items-center py-2 shrink-0 select-none">
      <div className="flex flex-col items-center gap-1 mt-1">
        {ICONS.map(({ view, icon, label }) => {
          const isActive = activeView === view;
          return (
            <button
              key={view}
              onClick={() => onSelect(view)}
              className={`
                relative w-9 h-9 rounded-lg flex items-center justify-center text-lg
                transition-all duration-150
                ${isActive
                  ? "bg-[#3a3a4a] text-white"
                  : "text-white/35 hover:text-white/60 hover:bg-white/5"
                }
              `}
              title={label}
            >
              {isActive && (
                <div className="absolute left-[-7px] w-[3px] h-[18px] bg-purple-400 rounded-r-full" />
              )}
              <span className="leading-none">{icon}</span>
            </button>
          );
        })}
      </div>

      <div className="flex-1" />

      <button
        onClick={onToggleDark}
        className="w-9 h-9 rounded-lg flex items-center justify-center text-lg
                   text-white/35 hover:text-white/60 hover:bg-white/5 transition-all duration-150"
        title={darkMode ? "浅色模式" : "深色模式"}
      >
        <span className="leading-none">{darkMode ? "☀️" : "🌙"}</span>
      </button>

      <button
        onClick={onSettings}
        className="w-9 h-9 rounded-lg flex items-center justify-center text-lg
                   text-white/35 hover:text-white/60 hover:bg-white/5 transition-all duration-150"
        title="设置"
      >
        <span className="leading-none">⚙</span>
      </button>
    </div>
  );
}
