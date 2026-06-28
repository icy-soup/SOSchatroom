import { useState, useCallback } from "react";
import { ALL_TOOLS } from "../tools/registry";
import { isToolEnabled, setToolEnabled } from "../tools/preferences";
import type { ToolDefinition } from "../tools/types";

export default function MarketView({ onSelectTool }: { onSelectTool: (id: string) => void }) {
  const [ver, setVer] = useState(0);

  const toggle = useCallback((toolId: string, current: boolean) => {
    setToolEnabled(toolId, !current);
    setVer((v) => v + 1);
  }, []);

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-white/30 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <h2 className="text-sm font-semibold text-[#2c2c2c]">🏪 工具市场</h2>
        <p className="text-xs text-black/30 mt-0.5">安装／卸载春日工具包中的插件</p>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="grid grid-cols-2 gap-3 max-w-2xl">
          {ALL_TOOLS.map((tool) => {
            const enabled = isToolEnabled(tool.id);
            return (
              <ToolCard key={tool.id} tool={tool}
                enabled={enabled}
                onToggle={() => toggle(tool.id, enabled)}
                onOpen={() => onSelectTool(tool.id)} />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function ToolCard({ tool, enabled, onToggle, onOpen }: {
  tool: ToolDefinition;
  enabled: boolean;
  onToggle: () => void;
  onOpen: () => void;
}) {
  return (
    <div className={`relative bg-white border rounded-xl p-4 transition-all duration-150
      ${enabled
        ? "border-black/10 shadow-sm hover:shadow-md"
        : "border-black/5 opacity-50"
      }`}>
      {/* Icon */}
      <div className="text-2xl mb-2">{tool.icon}</div>

      {/* Name */}
      <h3 className={`text-sm font-semibold mb-1 ${enabled ? "text-[#2c2c2c]" : "text-black/40"}`}>
        {tool.name}
      </h3>

      {/* Description */}
      <p className="text-[11px] text-black/35 leading-relaxed line-clamp-3 mb-3">
        {tool.description}
      </p>

      {/* Badge */}
      <div className="text-[10px] text-black/20 mb-3">
        {tool.kind === "control" ? "🛠 交互工具" : "🤖 AI 工具"}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button onClick={onToggle}
          className={`text-[11px] px-2.5 py-1.5 rounded-lg font-medium transition flex items-center gap-1
            ${enabled
              ? "bg-red-50 text-red-500 hover:bg-red-100"
              : "bg-purple-50 text-purple-600 hover:bg-purple-100"
            }`}>
          {enabled ? "✕ 卸载" : "✓ 安装"}
        </button>
        <button onClick={onOpen}
          className="text-[11px] bg-black/5 hover:bg-black/10 text-black/40 px-2.5 py-1.5 rounded-lg transition">
          打开
        </button>
      </div>
    </div>
  );
}
