import { useState } from "react";

interface SceneSettingsPanelProps {
  background: string;
  absent: string[];
  allCharacters: string[];
  onBackgroundChange: (v: string) => void;
  onAbsentChange: (v: string[]) => void;
}

export default function SceneSettingsPanel({
  background, absent, allCharacters,
  onBackgroundChange, onAbsentChange,
}: SceneSettingsPanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-t border-black/10 mt-4 pt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-black/40 hover:text-black/70 transition"
      >
        {open ? "▼" : "▶"} 场景设置
        {!open && (background || absent.length > 0) && (
          <span className="text-purple-500 ml-1">(已设置)</span>
        )}
      </button>

      {open && (
        <div className="mt-2 space-y-3">
          <div>
            <label className="text-[11px] text-black/40 block mb-1">场景背景词</label>
            <textarea
              className="w-full bg-white/80 border border-black/10 rounded-lg px-3 py-2 text-sm resize-none focus:border-purple-400 focus:outline-none placeholder-black/20"
              rows={3}
              placeholder="今天放学后春日说想去山上抓外星人……"
              value={background}
              onChange={(e) => onBackgroundChange(e.target.value)}
            />
          </div>
          <div>
            <label className="text-[11px] text-black/40 block mb-1">缺席角色</label>
            <div className="flex flex-wrap gap-1.5">
              {allCharacters.map((name) => (
                <button
                  key={name}
                  onClick={() => {
                    onAbsentChange(
                      absent.includes(name)
                        ? absent.filter((a) => a !== name)
                        : [...absent, name]
                    );
                  }}
                  className={`px-2.5 py-1 text-xs rounded-lg border transition ${
                    absent.includes(name)
                      ? "border-red-300 text-red-500 bg-red-50"
                      : "border-black/10 text-black/50 hover:border-black/20 hover:text-black/70"
                  }`}
                >
                  {absent.includes(name) ? `✕ ${name}` : name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
