import { useState, useEffect, useCallback, useRef } from "react";

/* ── Types ── */

interface TaskItem {
  id: string;
  text: string;
  completed: boolean;
}

interface CheckInRecord {
  timestamp: number;
  completedCount: number;
  totalCount: number;
  haruhiResponse: string;
}

interface SessionState {
  id: string;
  rawInput: string;
  plan: string;
  tasks: TaskItem[];
  checkIns: CheckInRecord[];
  createdAt: number;
}

interface HistoryEntry {
  id: string;
  sessionId: string;
  rawInput: string;
  plan: string;
  tasks: TaskItem[];
  checkIns: CheckInRecord[];
  createdAt: number;
  lastCheckinAt: number | null;
}

type Phase = "input" | "loading" | "tracking" | "checkin-loading" | "addtask-loading";

/* ── Constants ── */

const SESSIONS_KEY = "action_engine_sessions";
const HISTORY_KEY = "action_engine_history";
const OLD_STATE_KEY = "action_engine_state";
const API = "/api/action-engine";

const LOADING_MSGS = [
  "哼！急什么，我在排了！",
  "给我3秒——SOS团长的直觉正在全速运转！",
  "别催别催！我在用超能力分析了！",
  "好了好了，马上就好——你再等等！",
  "啧，你的单子还挺多……等着！",
];

/* ── Helpers ── */

function parseTasksFromPlan(plan: string): TaskItem[] {
  const tasks: TaskItem[] = [];
  for (const line of plan.split("\n")) {
    const m = line.match(/^(?:\d+|N)\.\s+(.+)/);
    if (m) {
      tasks.push({
        id: `t_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        text: m[1].replace(/\*\*/g, "").trim(),
        completed: false,
      });
    }
  }
  return tasks;
}

function renderMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}

let _sessionListCache: SessionState[] | null = null;

function loadSessions(): SessionState[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveSessions(s: SessionState[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(s));
    _sessionListCache = null;
  } catch { /* quota exceeded */ }
}

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch { /* quota exceeded */ }
}

function addHistoryEntry(session: SessionState) {
  const entries = loadHistory();
  const entry: HistoryEntry = {
    id: `h_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    sessionId: session.id,
    rawInput: session.rawInput,
    plan: session.plan,
    tasks: session.tasks,
    checkIns: session.checkIns,
    createdAt: session.createdAt,
    lastCheckinAt: session.checkIns.length > 0 ? session.checkIns[0].timestamp : null,
  };
  entries.unshift(entry);
  saveHistory(entries.slice(0, 50));
}

function migrateFromOldState(): SessionState | null {
  try {
    const raw = localStorage.getItem(OLD_STATE_KEY);
    if (!raw) return null;
    const old = JSON.parse(raw);
    if (!old || !old.plan) return null;
    const sessions = loadSessions();
    if (sessions.length > 0) return null;
    const session: SessionState = {
      id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      rawInput: old.rawInput || "",
      plan: old.plan || "",
      tasks: old.tasks || [],
      checkIns: old.checkIns || [],
      createdAt: old.createdAt || Date.now(),
    };
    localStorage.removeItem(OLD_STATE_KEY);
    return session;
  } catch {
    return null;
  }
}

/* ── Component ── */

export default function ActionEngine({ onBack }: { onBack: () => void }) {
  const [phase, setPhase] = useState<Phase>("input");
  const [sessions, setSessions] = useState<SessionState[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Current working session fields
  const [input, setInput] = useState("");
  const [plan, setPlan] = useState("");
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [checkIns, setCheckIns] = useState<CheckInRecord[]>([]);
  const [lastResponse, setLastResponse] = useState("");

  // Add-task dialog
  const [showAddTask, setShowAddTask] = useState(false);
  const [addTaskInput, setAddTaskInput] = useState("");
  const [addTaskResponse, setAddTaskResponse] = useState("");

  // UI state
  const [loadingMsg, setLoadingMsg] = useState("");
  const [dots, setDots] = useState("");
  const [error, setError] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [historyVer, setHistoryVer] = useState(0);

  const addTaskRef = useRef<HTMLTextAreaElement>(null);

  // On mount: load sessions & migrate old state
  useEffect(() => {
    let s = loadSessions();
    if (s.length === 0) {
      const migrated = migrateFromOldState();
      if (migrated) {
        s = [migrated];
        saveSessions(s);
      }
    }
    setSessions(s);
  }, []);

  /* ── Loading animation ── */
  useEffect(() => {
    if (phase !== "loading" && phase !== "checkin-loading" && phase !== "addtask-loading") {
      setLoadingMsg("");
      setDots("");
      return;
    }
    let idx = 0;
    setLoadingMsg(LOADING_MSGS[0]);
    const msgTimer = setInterval(() => {
      idx = (idx + 1) % LOADING_MSGS.length;
      setLoadingMsg(LOADING_MSGS[idx]);
    }, 3000);
    const dotTimer = setInterval(() => {
      setDots((p) => (p.length >= 3 ? "" : p + "."));
    }, 500);
    return () => { clearInterval(msgTimer); clearInterval(dotTimer); };
  }, [phase]);

  // Focus add-task textarea when shown
  useEffect(() => {
    if (showAddTask && addTaskRef.current) {
      addTaskRef.current.focus();
    }
  }, [showAddTask]);

  /* ── Persist current session info ── */
  const persistCurrentSession = useCallback((overrides: Partial<SessionState>) => {
    setSessions((prev) => {
      const updated = prev.map((s) =>
        s.id === activeId ? { ...s, ...overrides } : s
      );
      saveSessions(updated);
      return updated;
    });
  }, [activeId]);

  /* ── API Call ── */
  const callEngine = useCallback(async (type: "plan" | "checkin" | "add_tasks", content: string) => {
    setError("");
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, input: content }),
      });
      const data = await res.json();
      return data.result as string;
    } catch {
      setError("网络请求失败，检查后端是否启动");
      return null;
    }
  }, []);

  /* ── Clear working state ── */
  const clearWorkingState = useCallback(() => {
    setInput("");
    setPlan("");
    setTasks([]);
    setCheckIns([]);
    setLastResponse("");
    setError("");
    setShowAddTask(false);
    setAddTaskInput("");
    setAddTaskResponse("");
  }, []);

  /* ── Create new plan ── */
  const handleSubmit = useCallback(async () => {
    const txt = input.trim();
    if (!txt) return;
    setPhase("loading");
    setError("");
    const result = await callEngine("plan", txt);
    if (!result) { setPhase("input"); return; }

    const parsed = parseTasksFromPlan(result);
    const newSession: SessionState = {
      id: `s_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      rawInput: txt,
      plan: result,
      tasks: parsed,
      checkIns: [],
      createdAt: Date.now(),
    };

    const updated = [newSession, ...sessions];
    saveSessions(updated);
    setSessions(updated);
    setActiveId(newSession.id);
    setPlan(result);
    setTasks(parsed);
    setCheckIns([]);
    setLastResponse("");
    setPhase("tracking");
  }, [input, sessions, callEngine]);

  /* ── Resume a session ── */
  const handleResume = useCallback((s: SessionState) => {
    if (!s) return;
    setActiveId(s.id);
    setInput(s.rawInput);
    setPlan(s.plan);
    setTasks(s.tasks);
    setCheckIns(s.checkIns || []);
    setLastResponse(s.checkIns?.[0]?.haruhiResponse || "");
    setError("");
    setShowAddTask(false);
    setAddTaskInput("");
    setAddTaskResponse("");
    setPhase("tracking");
  }, []);

  /* ── Archive a session (remove from active) ── */
  const handleArchive = useCallback((session: SessionState) => {
    if (session.tasks.some((t) => t.completed) || session.checkIns.length > 0) {
      addHistoryEntry(session);
      setHistoryVer((v) => v + 1);
    }
    const updated = sessions.filter((s) => s.id !== session.id);
    saveSessions(updated);
    setSessions(updated);
    if (activeId === session.id) {
      setActiveId(null);
      clearWorkingState();
      setPhase("input");
    }
  }, [sessions, activeId, clearWorkingState]);

  /* ── Go back to session list ── */
  const goToSessionList = useCallback(() => {
    // Save current state before going back
    if (activeId) {
      persistCurrentSession({ plan, tasks, checkIns });
    }
    setActiveId(null);
    clearWorkingState();
    setPhase("input");
  }, [activeId, plan, tasks, checkIns, persistCurrentSession, clearWorkingState]);

  /* ── Toggle task ── */
  const toggleTask = useCallback((id: string) => {
    setTasks((prev) => {
      const next = prev.map((t) =>
        t.id === id ? { ...t, completed: !t.completed } : t
      );
      persistCurrentSession({ tasks: next });
      return next;
    });
  }, [persistCurrentSession]);

  /* ── Check-in ── */
  const handleCheckin = useCallback(async () => {
    const done = tasks.filter((t) => t.completed);
    const remaining = tasks.filter((t) => !t.completed);
    const content = [
      `【已完成 ${done.length}/${tasks.length}】`,
      done.length > 0 ? "已完成：\n" + done.map((t) => `✅ ${t.text}`).join("\n") : "一个都没做……",
      remaining.length > 0 ? "\n未完成：\n" + remaining.map((t) => `❌ ${t.text}`).join("\n") : "\n全部完成了！",
      `\n原始计划：${plan.slice(0, 500)}`,
    ].join("\n");

    setPhase("checkin-loading");
    const result = await callEngine("checkin", content);
    if (!result) { setPhase("tracking"); return; }

    const record: CheckInRecord = {
      timestamp: Date.now(),
      completedCount: done.length,
      totalCount: tasks.length,
      haruhiResponse: result,
    };
    const updatedCheckIns = [record, ...checkIns];
    setCheckIns(updatedCheckIns);
    setLastResponse(result);
    persistCurrentSession({ checkIns: updatedCheckIns, tasks });
    setPhase("tracking");
  }, [tasks, plan, checkIns, callEngine, persistCurrentSession]);

  /* ── Add tasks via LLM dialogue ── */
  const handleAddTask = useCallback(async () => {
    const txt = addTaskInput.trim();
    if (!txt) return;

    const tasksContext = tasks.map((t, i) => `${i + 1}. ${t.text}`).join("\n");
    const fullInput = `【当前未完成任务】\n${tasksContext}\n\n【我想追加】\n${txt}\n\n---\n请帮我追加到清单里！`;

    setPhase("addtask-loading");
    const result = await callEngine("add_tasks", fullInput);
    if (!result) { setPhase("tracking"); return; }

    const newTasks = parseTasksFromPlan(result);
    const updatedTasks = [...tasks, ...newTasks];
    setTasks(updatedTasks);
    setAddTaskResponse(result);
    persistCurrentSession({ tasks: updatedTasks });
    setAddTaskInput("");
    setPhase("tracking");
  }, [addTaskInput, tasks, callEngine, persistCurrentSession]);

  /* ── Delete a single check-in record ── */
  const deleteCheckin = useCallback((index: number) => {
    const updated = checkIns.filter((_, i) => i !== index);
    setCheckIns(updated);
    persistCurrentSession({ checkIns: updated });
    if (updated.length === 0) setLastResponse("");
    else if (index === 0) setLastResponse(updated[0]?.haruhiResponse || "");
  }, [checkIns, persistCurrentSession]);

  /* ── Load from history ── */
  const loadFromHistory = useCallback((entry: HistoryEntry) => {
    const restored: SessionState = {
      id: `s_restored_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      rawInput: entry.rawInput,
      plan: entry.plan,
      tasks: entry.tasks,
      checkIns: entry.checkIns || [],
      createdAt: Date.now(),
    };
    const updated = [restored, ...sessions];
    saveSessions(updated);
    setSessions(updated);
    setActiveId(restored.id);
    setInput(restored.rawInput);
    setPlan(restored.plan);
    setTasks(restored.tasks);
    setCheckIns(restored.checkIns);
    setLastResponse(restored.checkIns?.[0]?.haruhiResponse || "");
    setShowHistory(false);
    setPhase("tracking");
  }, [sessions]);

  const deleteHistory = useCallback((id: string) => {
    const entries = loadHistory().filter((e) => e.id !== id);
    saveHistory(entries);
    setHistoryVer((v) => v + 1);
  }, []);

  /* ── Format date ── */
  const fmtDate = (ts: number) => {
    const d = new Date(ts);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
  };

  const completed = tasks.filter((t) => t.completed).length;
  const total = tasks.length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  const historyEntries = loadHistory();

  /* ── Render ── */

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-white/30 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2.5">
          {phase === "tracking" ? (
            <button onClick={goToSessionList}
              className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">
              ← 清单
            </button>
          ) : (
            <button onClick={onBack}
              className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">
              ← 返回
            </button>
          )}
          <span className="text-black/20">|</span>
          <span className="text-lg leading-none">⚡</span>
          <h2 className="text-sm font-semibold text-[#2c2c2c]">春日行动引擎</h2>
        </div>
        {phase === "input" && (
          <button onClick={() => setShowHistory(!showHistory)}
            className={`text-sm transition px-2 py-1 rounded ${
              showHistory
                ? "text-purple-500 bg-purple-50"
                : "text-black/40 hover:text-black/60 hover:bg-black/5"
            }`}
            title="历史记录">
            📄
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 max-w-2xl mx-auto w-full">
        {/* ── INPUT PHASE: session list + new plan ── */}
        {phase === "input" && (
          <>
            {/* Active sessions list */}
            {sessions.length > 0 && (
              <div className="mb-5">
                <div className="text-xs font-medium text-[#2c2c2c]/50 mb-2 flex items-center gap-1.5">
                  <span>📋 活跃清单</span>
                  <span className="text-[10px] text-black/20">({sessions.length})</span>
                </div>
                <div className="space-y-2">
                  {sessions.map((s) => {
                    const done = s.tasks.filter((t) => t.completed).length;
                    return (
                      <div key={s.id}
                        className="flex items-center gap-3 p-3 bg-white border border-black/5 rounded-xl hover:border-purple-200/60 transition group">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-[#2c2c2c] font-medium truncate">
                              {s.rawInput.slice(0, 50)}{s.rawInput.length > 50 ? "…" : ""}
                            </span>
                            <span className="text-[10px] text-black/20 shrink-0">
                              {fmtDate(s.createdAt)}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[11px] text-black/30">
                              ✅ {done}/{s.tasks.length}
                            </span>
                            {s.checkIns.length > 0 && (
                              <span className="text-[11px] text-black/20">
                                · 汇报 {s.checkIns.length} 次
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-1.5 shrink-0">
                          <button onClick={() => handleResume(s)}
                            className="text-xs bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg font-medium transition">
                            继续
                          </button>
                          <button onClick={() => handleArchive(s)}
                            className="text-xs bg-black/5 hover:bg-red-50 hover:text-red-400 text-black/40 px-2.5 py-1.5 rounded-lg transition"
                            title="归档">
                            🗂️
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* New plan */}
            <p className="text-sm text-black/40 mb-4">
              把待办和截止日期全丢过来！本团长一口气给你排好顺序！
            </p>

            <textarea value={input} onChange={(e) => setInput(e.target.value)}
              placeholder={"把待办和期限丢过来：\n1. 写周报（明天截止）\n2. 健身（拖一个月了）\n3. ..."}
              rows={10}
              className="w-full bg-white border border-black/10 rounded-xl px-4 py-3 text-sm resize-none focus:border-purple-400 focus:outline-none placeholder-black/20" />

            {error && (
              <div className="text-red-500 text-xs bg-red-50/50 rounded-lg px-3 py-2 mt-3">
                {error}
              </div>
            )}
          </>
        )}

        {/* ── LOADING PHASE ── */}
        {(phase === "loading" || phase === "checkin-loading" || phase === "addtask-loading") && (
          <div className="bg-white/80 border border-black/5 rounded-xl px-5 py-10 flex flex-col items-center gap-4 min-h-[240px] justify-center">
            <span className="inline-block w-8 h-8 border-[3px] border-purple-300/40 border-t-purple-600 rounded-full animate-spin" />
            <span className="text-sm text-black/40 text-center leading-relaxed">
              {loadingMsg}<span className="inline-block w-4 text-left">{dots}</span>
            </span>
            {phase === "loading" && (
              <div className="w-full max-w-md mt-2">
                <div className="text-xs text-black/20 mb-1">你的输入</div>
                <div className="bg-white border border-black/5 rounded-xl px-4 py-3 text-sm text-black/70 whitespace-pre-wrap leading-relaxed line-clamp-5">
                  {input}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TRACKING PHASE ── */}
        {phase === "tracking" && (
          <>
            {/* Left: Haruhi's evaluation / Right: checklist */}
            <div className="flex gap-4 flex-col md:flex-row">
              <div className="flex-1 min-w-0">
                <div className="text-xs text-black/20 mb-1">⚡ 春日评价</div>
                <div className="bg-white border border-black/5 rounded-xl px-5 py-4 text-sm text-[#2c2c2c]/80 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(plan) }} />
              </div>

              <div className="w-full md:w-[320px] shrink-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#2c2c2c]">📋 日程表</span>
                  <span className="text-xs text-black/30">{completed}/{total}</span>
                </div>

                <div className="w-full h-1.5 bg-black/5 rounded-full mb-3 overflow-hidden">
                  <div className="h-full bg-purple-500 rounded-full transition-all duration-300"
                    style={{ width: `${pct}%` }} />
                </div>

                <div className="bg-white border border-black/5 rounded-xl max-h-[60vh] overflow-y-auto">
                  {tasks.length === 0 ? (
                    <div className="px-4 py-6 text-center text-sm text-black/20">没有任务</div>
                  ) : (
                    <div className="divide-y divide-black/5">
                      {tasks.map((t) => (
                        <label key={t.id}
                          className="flex items-start gap-3 px-4 py-2.5 hover:bg-black/[0.02] cursor-pointer transition">
                          <input type="checkbox" checked={t.completed}
                            onChange={() => toggleTask(t.id)}
                            className="mt-0.5 w-4 h-4 rounded border-black/20 text-purple-600
                              focus:ring-purple-400 accent-purple-600 cursor-pointer" />
                          <span className={`text-sm flex-1 leading-relaxed ${t.completed ? "line-through text-black/25" : "text-[#2c2c2c]/80"}`}>
                            {t.text}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Add-task response bubble */}
            {addTaskResponse && (
              <div className="bg-amber-50/70 border border-amber-200/50 rounded-xl p-4 mt-4">
                <div className="text-xs text-amber-600 font-medium mb-1.5">📝 春日说（追加任务）：</div>
                <div className="text-sm text-[#2c2c2c]/80 whitespace-pre-wrap leading-relaxed">
                  {addTaskResponse}
                </div>
              </div>
            )}

            {/* Last check-in response */}
            {lastResponse && (
              <div className="bg-purple-50/60 border border-purple-200/50 rounded-xl p-4 mt-4">
                <div className="text-xs text-purple-500 font-medium mb-1.5">⚡ 春日说：</div>
                <div className="text-sm text-[#2c2c2c]/80 whitespace-pre-wrap leading-relaxed">
                  {lastResponse}
                </div>
                <div className="text-[10px] text-black/20 mt-1.5">
                  {fmtDate(checkIns[0]?.timestamp || Date.now())}
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="text-red-500 text-xs bg-red-50/50 rounded-lg px-3 py-2 mt-4">
                {error}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2 flex-wrap mt-4">
              <button onClick={handleCheckin}
                disabled={total === 0}
                className="flex-1 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition shadow-sm">
                {total === 0 ? "没有任务" : "向春日汇报！"}
              </button>
              <button onClick={() => { setShowAddTask(true); setAddTaskResponse(""); }}
                className="bg-amber-500 hover:bg-amber-400 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition shadow-sm">
                + 添加任务
              </button>
              <button onClick={() => {
                const s = sessions.find((s) => s.id === activeId);
                if (s) handleArchive(s);
              }}
                className="bg-black/5 hover:bg-black/10 text-black/40 px-4 py-2.5 rounded-xl text-sm transition">
                完成归档
              </button>
            </div>

            {/* Add-task dialog */}
            {showAddTask && (
              <div className="mt-3 bg-amber-50/60 border border-amber-200/50 rounded-xl p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-amber-700">📝 和春日对话 · 新增任务</span>
                  <button onClick={() => setShowAddTask(false)}
                    className="text-xs text-black/20 hover:text-black/50">✕</button>
                </div>
                <textarea ref={addTaskRef} value={addTaskInput}
                  onChange={(e) => setAddTaskInput(e.target.value)}
                  placeholder={"比如：\n我还要做PPT和买生日礼物"}
                  rows={3}
                  className="w-full bg-white border border-amber-200/60 rounded-lg px-3 py-2 text-sm resize-none focus:border-amber-400 focus:outline-none placeholder-black/20" />
                <div className="flex justify-end mt-2">
                  <button onClick={handleAddTask} disabled={!addTaskInput.trim()}
                    className="bg-amber-500 hover:bg-amber-400 disabled:bg-amber-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition shadow-sm">
                    发送给春日
                  </button>
                </div>
              </div>
            )}

            {/* Check-in history */}
            {checkIns.length > 0 && (
              <details className="group mt-4">
                <summary className="text-xs text-black/30 hover:text-black/50 cursor-pointer select-none">
                  汇报记录（{checkIns.length} 次）▼
                </summary>
                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                  {checkIns.map((c, i) => (
                    <div key={i}
                      className="bg-white border border-black/5 rounded-lg px-3 py-2 relative group">
                      <button onClick={() => deleteCheckin(i)}
                        className="absolute top-1.5 right-1.5 w-5 h-5 flex items-center justify-center rounded text-[11px] text-black/20 hover:text-red-400 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition"
                        title="删除这条汇报记录">✕</button>
                      <div className="flex items-center justify-between text-[10px] text-black/20 mb-1">
                        <span>第 {checkIns.length - i} 次汇报</span>
                        <span>{fmtDate(c.timestamp)}</span>
                      </div>
                      <div className="text-xs text-black/40 mb-1">
                        完成 {c.completedCount}/{c.totalCount}
                      </div>
                      <div className="text-xs text-[#2c2c2c]/70 whitespace-pre-wrap line-clamp-3">
                        {c.haruhiResponse}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      {phase === "input" && (
        <div className="px-6 py-3 border-t border-black/5 bg-white/60 shrink-0 max-w-2xl mx-auto w-full flex justify-end gap-2">
          <button onClick={handleSubmit} disabled={!input.trim()}
            className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition">
            让春日安排！
          </button>
        </div>
      )}

      {/* ── History panel ── */}
      {showHistory && (
        <>
          <div className="absolute inset-0 bg-black/10 z-20"
            onClick={() => setShowHistory(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-80 bg-white border-l border-black/10 shadow-xl z-30 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-black/5 shrink-0">
              <span className="text-sm font-medium text-[#2c2c2c]">规划历史</span>
              <button onClick={() => setShowHistory(false)}
                className="text-black/20 hover:text-black/50 text-sm">✕</button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
              {historyEntries.length === 0 ? (
                <p className="text-xs text-black/20 text-center py-8">暂无历史记录</p>
              ) : (
                historyEntries.map((entry) => {
                  const done = entry.tasks.filter((t) => t.completed).length;
                  return (
                    <div key={entry.id}
                      className="group relative bg-white rounded-lg border border-black/5 hover:border-purple-200 hover:bg-purple-50/30 transition cursor-pointer"
                      onClick={() => loadFromHistory(entry)}>
                      <div className="px-3 py-2">
                        <div className="flex items-center justify-between">
                          <div className="text-[10px] text-black/20">{fmtDate(entry.createdAt)}</div>
                          <span className="text-[10px] text-purple-400 opacity-0 group-hover:opacity-100 transition">恢复</span>
                        </div>
                        <div className="text-xs text-black/60 line-clamp-2 mt-0.5 pr-5">
                          {entry.rawInput.slice(0, 80)}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-black/25">
                            ✅ {done}/{entry.tasks.length}
                          </span>
                          {entry.lastCheckinAt && (
                            <span className="text-[10px] text-black/20">
                              · 最后汇报 {fmtDate(entry.lastCheckinAt)}
                            </span>
                          )}
                        </div>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); deleteHistory(entry.id); }}
                        className="absolute top-1.5 right-1.5 w-5 h-5 flex items-center justify-center rounded text-[11px] text-black/20 hover:text-red-400 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition"
                        title="删除">✕</button>
                    </div>
                  );
                })
              )}
            </div>
            {historyEntries.length > 0 && (
              <div className="px-3 py-2 border-t border-black/5 shrink-0">
                <button onClick={() => { saveHistory([]); setHistoryVer((v) => v + 1); }}
                  className="text-[11px] text-red-400 hover:text-red-300">清空历史</button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
