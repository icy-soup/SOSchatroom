import { useState, useCallback, useEffect } from "react";
import type { ToolDefinition } from "./types";
import { getToolHistory, clearToolHistory, deleteToolHistoryEntry } from "./storage";
import type { ToolHistoryEntry } from "./storage";

interface LlmToolViewProps {
  tool: ToolDefinition;
  draft: string;
  result: string;
  loading: boolean;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onBack: () => void;
  onRetry: () => void;
  onLoadHistory?: (input: string, output: string) => void;
}

/** 每个工具的专属 loading 消息（角色口吻），循环显示 */
const LOADING_MSGS: Record<string, string[]> = {
  action_engine: [
    "哼！急什么，我在排了！",
    "给我3秒——SOS团长的直觉正在全速运转！",
    "别催别催！我在用超能力分析了！",
    "好了好了，马上就好——你再等等！",
    "啧，你的单子还挺多……等着！",
  ],
  vitality_radar: [
    "让我看看你今天又干了什么好事——",
    "嗯——能量扫描中，你的状态我一眼就能看穿！",
    "哈！找到了——你的问题在这儿！",
    "雷达全开！别急，跑不掉的。",
    "哼，你今天的活力值……待我算算！",
  ],
  anti_inspiration: [
    "……唉，鸡汤是吧。等我一下。",
    "啊——（哈欠）让我看看你又信了什么鬼话。",
    "……行吧，我在拆了。",
    "啧，又是这种……稍等，我想想怎么吐槽。",
    "…………（懒得说话，但在看）",
  ],
};

const FALLBACK_MSGS = ["处理中……", "稍等一下……", "马上就好……"];

/** 简单渲染 markdown：**bold** → strong，\n → <br/> */
function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(
      /^(\d+)\.\s+(.+)/gm,
      '<div style="display:flex;gap:0.5em"><span style="min-width:1.5em;flex-shrink:0">$1.</span><span>$2</span></div>',
    )
    .replace(/\n/g, "<br/>");
}

/** LLM 型工具通用界面：描述 → 输入框 → 提交 → 结果展示 */
export default function LlmToolView({
  tool,
  draft,
  result,
  loading,
  onChange,
  onSubmit,
  onBack,
  onRetry,
  onLoadHistory,
}: LlmToolViewProps) {
  const [showHistory, setShowHistory] = useState(false);
  const [histVer, setHistVer] = useState(0);
  const history = getToolHistory(tool.id);

  const deleteEntry = useCallback((entryId: string) => {
    deleteToolHistoryEntry(tool.id, entryId);
    setHistVer((v) => v + 1);
  }, [tool.id]);

  /* ── loading 时循环角色口吻消息 ── */
  const [loadingMsg, setLoadingMsg] = useState("");
  const [dots, setDots] = useState("");

  useEffect(() => {
    if (!loading) {
      setLoadingMsg("");
      setDots("");
      return;
    }

    const msgs = LOADING_MSGS[tool.id] ?? FALLBACK_MSGS;
    let idx = 0;
    setLoadingMsg(msgs[0]);

    const msgTimer = setInterval(() => {
      idx = (idx + 1) % msgs.length;
      setLoadingMsg(msgs[idx]);
    }, 3500);

    const dotTimer = setInterval(() => {
      setDots((p) => (p.length >= 3 ? "" : p + "."));
    }, 500);

    return () => {
      clearInterval(msgTimer);
      clearInterval(dotTimer);
    };
  }, [loading, tool.id]);

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  };

  const clearHistoryAndClose = useCallback(() => {
    clearToolHistory(tool.id);
    setShowHistory(false);
  }, [tool.id]);

  const loadingView = loading && (
    <div className="bg-white/80 border border-black/5 rounded-xl px-5 py-8 flex flex-col items-center gap-3 min-h-[140px] justify-center">
      <span className="inline-block w-7 h-7 border-[3px] border-purple-200 border-t-purple-600 rounded-full animate-spin" />
      <span className="text-sm text-black/40 text-center leading-relaxed">
        {loadingMsg}
        <span className="inline-block w-4 text-left">{dots}</span>
      </span>
    </div>
  );

  const resultView = !loading && result && (
    <div
      className="bg-white border border-black/5 rounded-xl px-5 py-4 text-sm text-[#2c2c2c]/80 leading-relaxed"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(result) }}
    />
  );

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-white/30 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2.5">
          <button
            onClick={onBack}
            className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5"
          >
            ← 返回
          </button>
          <span className="text-black/20">|</span>
          <span className="text-lg leading-none">{tool.icon}</span>
          <h2 className="text-sm font-semibold text-[#2c2c2c]">{tool.name}</h2>
        </div>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className={`text-sm transition px-2 py-1 rounded ${
            showHistory
              ? "text-purple-500 bg-purple-50"
              : "text-black/40 hover:text-black/60 hover:bg-black/5"
          }`}
          title="历史记录"
        >
          📄
        </button>
      </div>

      {/* Body — 唯一可滚动区域 */}
      <div className="flex-1 overflow-y-auto px-6 py-5 max-w-2xl mx-auto w-full">
        {result || loading ? (
          <>
            <div className="mb-4">
              <div className="text-xs text-black/30 mb-1.5 font-medium">你的输入</div>
              <div className="bg-white/80 border border-black/5 rounded-xl px-4 py-3 text-sm text-[#2c2c2c]/70 whitespace-pre-wrap leading-relaxed">
                {draft}
              </div>
            </div>
            <div>
              <div className="text-xs text-black/30 mb-1.5 font-medium">
                {loading ? "正在分析" : "结果"}
              </div>
              {loadingView}
              {resultView}
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-black/40 mb-4">{tool.description}</p>
            <textarea
              value={draft}
              onChange={(e) => onChange(e.target.value)}
              placeholder={tool.placeholder}
              rows={8}
              className="w-full bg-white border border-black/10 rounded-xl px-4 py-3 text-sm resize-none focus:border-purple-400 focus:outline-none placeholder-black/20"
            />
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-black/5 bg-white/60 shrink-0 max-w-2xl mx-auto w-full flex justify-end gap-2">
        {result && !loading ? (
          <>
            <button
              onClick={onRetry}
              className="text-xs bg-black/5 hover:bg-black/10 text-black/50 px-3 py-1.5 rounded-lg font-medium transition"
            >
              重新输入
            </button>
            <button
              onClick={onSubmit}
              className="text-xs bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg font-medium transition"
            >
              再次分析
            </button>
          </>
        ) : (
          <button
            onClick={onSubmit}
            disabled={!draft.trim() || loading}
            className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
          >
            {loading ? "分析中..." : "分析"}
          </button>
        )}
      </div>

      {/* ── 历史面板（浮层） ── */}
      {showHistory && (
        <>
          <div
            className="absolute inset-0 bg-black/10 z-20"
            onClick={() => setShowHistory(false)}
          />
          <div className="absolute right-0 top-0 bottom-0 w-80 bg-white border-l border-black/10 shadow-xl z-30 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-black/5 shrink-0">
              <span className="text-sm font-medium text-[#2c2c2c]">历史记录</span>
              <button
                onClick={() => setShowHistory(false)}
                className="text-black/20 hover:text-black/50 text-sm"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
              {history.length === 0 ? (
                <p className="text-xs text-black/20 text-center py-8">暂无历史记录</p>
              ) : (
                <div className="space-y-2">
                  <p className="text-[10px] text-black/20 px-1">点击条目加载到主界面</p>
                  {history.map((entry) => (
                    <HistoryCard
                      key={entry.id}
                      entry={entry}
                      formatDate={formatDate}
                      onSelect={() => {
                        onLoadHistory?.(entry.input, entry.output);
                        setShowHistory(false);
                      }}
                      onDelete={() => deleteEntry(entry.id)}
                    />
                  ))}
                </div>
              )}
            </div>
            {history.length > 0 && (
              <div className="px-3 py-2 border-t border-black/5 shrink-0">
                <button
                  onClick={clearHistoryAndClose}
                  className="text-[11px] text-red-400 hover:text-red-300"
                >
                  清空历史
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function HistoryCard({
  entry,
  formatDate,
  onSelect,
  onDelete,
}: {
  entry: ToolHistoryEntry;
  formatDate: (ts: number) => string;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="group relative bg-white rounded-lg border border-black/5 hover:border-purple-200 hover:bg-purple-50/30 transition cursor-pointer"
      onClick={onSelect}
    >
      <div className="px-3 py-2">
        <div className="flex items-center justify-between">
          <div className="text-[10px] text-black/20">{formatDate(entry.timestamp)}</div>
          <span className="text-[10px] text-purple-400 opacity-0 group-hover:opacity-100 transition">加载</span>
        </div>
        <div className="text-xs text-black/60 line-clamp-2 mt-0.5 pr-5">{entry.input}</div>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="absolute top-1.5 right-1.5 w-5 h-5 flex items-center justify-center rounded text-[11px] text-black/20 hover:text-red-400 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition"
        title="删除"
      >
        ✕
      </button>
    </div>
  );
}
