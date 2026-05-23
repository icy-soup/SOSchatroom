import { useState } from "react";

const TOOL_DESC: Record<string, { icon: string; name: string; desc: string; placeholder: string }> = {
  boredom_checker: {
    icon: "🔍",
    name: "反无聊审查器",
    desc: "把你的待办清单扔过来，我帮你分清楚哪些是真该做的，哪些是你在拖。",
    placeholder: "把待办发过来吧：\n1. 写周报\n2. 健身\n3. 回邮件\n...",
  },
  intuition_booster: {
    icon: "⚡",
    name: "直觉加速器",
    desc: "纠结来纠结去最烦了。给我三秒，给你一个直觉判断和行动方案。",
    placeholder: "说说你在纠结什么……",
  },
  action_tester: {
    icon: "💪",
    name: "行动力测试",
    desc: "有个计划拖了很久？让我打分——我做这事要多久，你为什么做不到。",
    placeholder: "把那个一直拖着没做的计划告诉我……",
  },
};

interface ToolPanelProps {
  toolId: string;
  userInput: string;
  result: string;
  loading: boolean;
  onBack: () => void;
  onSubmit: (toolId: string, content: string) => void;
  onRetry: () => void;
}

export default function ToolPanel({
  toolId,
  userInput,
  result,
  loading,
  onBack,
  onSubmit,
  onRetry,
}: ToolPanelProps) {
  const info = TOOL_DESC[toolId] ?? { icon: "🛠️", name: toolId, desc: "", placeholder: "" };
  const [draft, setDraft] = useState("");

  // 输入模式：用户还没提交
  if (!userInput && !loading && !result) {
    return (
      <main className="flex-1 flex flex-col min-w-0 bg-white/40">
        <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-2">
            <button onClick={onBack} className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">← 返回聊天</button>
            <span className="text-black/20">|</span>
            <span className="text-lg">{info.icon}</span>
            <h2 className="text-sm font-bold text-[#2c2c2c]">{info.name}</h2>
          </div>
        </div>
        <div className="flex-1 flex flex-col px-6 py-6 max-w-2xl mx-auto w-full">
          <p className="text-sm text-black/40 mb-4">{info.desc}</p>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={info.placeholder}
            rows={8}
            className="w-full bg-white border border-black/10 rounded-xl px-4 py-3 text-sm resize-none
                       focus:border-purple-400 focus:outline-none placeholder-black/20 flex-1"
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={() => onSubmit(toolId, draft.trim())}
              disabled={!draft.trim()}
              className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
            >
              分析
            </button>
          </div>
        </div>
      </main>
    );
  }

  // 结果模式
  return (
    <main className="flex-1 flex flex-col min-w-0 bg-white/40">
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2">
          <button onClick={onBack} className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">← 返回聊天</button>
          <span className="text-black/20">|</span>
          <span className="text-lg">{info.icon}</span>
          <h2 className="text-sm font-bold text-[#2c2c2c]">{info.name}</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 max-w-2xl mx-auto w-full">
        {userInput && (
          <div className="mb-5">
            <div className="text-xs text-black/30 mb-1.5 font-medium">你的输入</div>
            <div className="bg-white/80 border border-black/5 rounded-xl px-4 py-3 text-sm text-[#2c2c2c]/70 whitespace-pre-wrap leading-relaxed">
              {userInput}
            </div>
          </div>
        )}

        <div>
          <div className="text-xs text-black/30 mb-1.5 font-medium">分析结果</div>
          {loading ? (
            <div className="bg-white/80 border border-black/5 rounded-xl px-4 py-12 flex flex-col items-center gap-2">
              <span className="inline-block w-6 h-6 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin" />
              <span className="text-xs text-black/30">{info.name} 分析中...</span>
            </div>
          ) : (
            <div className="bg-white border border-black/5 rounded-xl px-4 py-4 text-sm text-[#2c2c2c]/80 whitespace-pre-wrap leading-relaxed">
              {result}
            </div>
          )}
        </div>
      </div>

      {result && !loading && (
        <div className="px-5 py-3 border-t border-black/5 bg-white/60 flex justify-end gap-2 max-w-2xl mx-auto w-full">
          <button
            onClick={onRetry}
            className="text-xs bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg font-medium transition"
          >
            重新分析
          </button>
        </div>
      )}
    </main>
  );
}
