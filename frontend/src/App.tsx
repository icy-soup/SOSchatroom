import { useState, useCallback, useRef, useEffect } from "react";
import type { Message, ChatConfig, WsMessage, PanelView, Conversation } from "./types";
import { useWebSocket } from "./hooks/useWebSocket";
import IconBar from "./components/IconBar";
import MiddlePanel from "./components/MiddlePanel";
import ChatArea from "./components/ChatArea";
import ChatHeader from "./components/ChatHeader";
import NewConversationView from "./components/NewConversationView";
import ContactDetail from "./components/ContactDetail";
import InputArea from "./components/InputArea";
import SettingsModal from "./components/SettingsModal";

let msgCounter = 0;
function nextId() {
  return `msg_${++msgCounter}`;
}

const TOOL_DESC: Record<string, { icon: string; name: string; desc: string; placeholder: string }> = {
  boredom_checker: {
    icon: "🔍", name: "反无聊审查器",
    desc: "喂！把你的待办清单交出来！我一眼就能看出哪些是你真的该做、哪些是你光在那边拖拖拉拉的！别想糊弄我！",
    placeholder: "把待办发过来吧：\n1. 写周报\n2. 健身\n3. 回邮件\n...",
  },
  intuition_booster: {
    icon: "⚡", name: "直觉加速器",
    desc: "哼！纠结来纠结去的最烦人了！给我三秒钟，一个直觉判断加行动方案——你有意见吗？",
    placeholder: "说说你在纠结什么……",
  },
  action_tester: {
    icon: "💪", name: "行动力测试",
    desc: "有个计划拖了很久是吧？拿来让我打分！我倒要看看你磨蹭个什么劲——这种事情换我来十分钟就搞定了！",
    placeholder: "把那个一直拖着没做的计划告诉我……",
  },
};

export default function App() {
  /* ── 对话存储（前端本地管理） ── */
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    try {
      const saved = localStorage.getItem("sos_conversations");
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [showNewConv, setShowNewConv] = useState(false);

  /* ── localStorage 持久化 ── */
  useEffect(() => {
    localStorage.setItem("sos_conversations", JSON.stringify(conversations));
  }, [conversations]);

  /* ── 后端同步状态 ── */
  const [myCharacter, setMyCharacter] = useState<string | null>(null);
  const [config, setConfig] = useState<ChatConfig>({
    demoMode: true, hasApiKey: false,
    apiUrl: "https://api.deepseek.com", model: "deepseek-v4-flash",
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [thinkingCharacters, setThinkingCharacters] = useState<string[]>([]);
  const [stylizeResult, setStylizeResult] = useState<{
    original: string; transformed: string | null;
    already_in_character: boolean; message: string;
  } | null>(null);
  const [isStylizing, setIsStylizing] = useState(false);

  /* ── 面板状态 ── */
  const [activePanel, setActivePanel] = useState<PanelView>("chat");
  const [selectedContact, setSelectedContact] = useState<string | null>(null);

  /* ── 新建对话预选（从联系人点进来时自动填入聊天对象） ── */
  const [newConvPreset, setNewConvPreset] = useState<string | null>(null);

  /* ── 工具状态 ── */
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [toolDraft, setToolDraft] = useState("");
  const [toolResult, setToolResult] = useState("");
  const [toolLoading, setToolLoading] = useState(false);

  /* ── 当前对话派生状态 ── */
  const activeConv = conversations.find((c) => c.id === activeConvId) ?? null;
  const messages = activeConv?.messages ?? [];
  const partnerName = activeConv?.partner ?? null;

  /* ── refs ── */
  const myCharRef = useRef<string | null>(null);
  const activeConvIdRef = useRef<string | null>(null);
  myCharRef.current = myCharacter;
  activeConvIdRef.current = activeConvId;

  // join 后恢复消息（扮演角色不同时）
  const pendingRestoreRef = useRef<Message[] | null>(null);

  /* ── 背景 ── */
  useEffect(() => {
    fetch("/api/background")
      .then((r) => r.json())
      .then((data) => {
        if (data.url) {
          document.body.style.backgroundImage = `url(${data.url})`;
          document.body.style.backgroundSize = "cover";
          document.body.style.backgroundPosition = "center";
          document.body.style.backgroundAttachment = "fixed";
        }
      })
      .catch(() => {});
    return () => {
      document.body.style.backgroundImage = "";
      document.body.style.backgroundSize = "";
      document.body.style.backgroundPosition = "";
      document.body.style.backgroundAttachment = "";
    };
  }, []);

  /* ── 系统消息：写入当前对话 ── */
  function addSystemMsg(text: string) {
    const msg: Message = { id: nextId(), character: "__system__", text, isBot: false };
    const id = activeConvIdRef.current;
    if (id) {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === id ? { ...c, messages: [...c.messages, msg] } : c
        )
      );
    }
  }

  /* ── WebSocket ── */
  const onWsMessage = useCallback((msg: WsMessage) => {
    switch (msg.type) {
      case "config":
        setConfig({
          demoMode: msg.demo_mode, hasApiKey: msg.has_api_key,
          apiUrl: msg.api_url, model: msg.model,
        });
        setIsConnected(true);
        break;

      case "config_updated":
        setConfig((prev) => ({
          ...prev, demoMode: msg.demo_mode, hasApiKey: msg.has_api_key,
          apiUrl: msg.api_url, model: msg.model,
        }));
        setSettingsOpen(false);
        addSystemMsg(msg.has_api_key ? "配置已保存，AI模式已开启" : "已切换为演示模式");
        break;

      case "character_ready":
        setMyCharacter(msg.character);
        if (pendingRestoreRef.current) {
          const restore = pendingRestoreRef.current;
          pendingRestoreRef.current = null;
          setConversations((prev) =>
            prev.map((c) =>
              c.id === activeConvIdRef.current ? { ...c, messages: restore } : c
            )
          );
        } else {
          addSystemMsg(`你以 ${msg.character} 的身份加入了聊天室`);
        }
        break;

      case "message": {
        const m: Message = { id: nextId(), character: msg.character, text: msg.text, isBot: msg.is_bot };
        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeConvIdRef.current ? { ...c, messages: [...c.messages, m] } : c
          )
        );
        break;
      }

      case "stylized":
        setStylizeResult(msg);
        setIsStylizing(false);
        break;

      case "thinking":
        setThinkingCharacters((prev) => [...prev, msg.character]);
        break;

      case "thinking_clear":
        setThinkingCharacters((prev) => prev.filter((c) => c !== msg.character));
        break;

      case "system":
        addSystemMsg(msg.text);
        break;

      case "error":
        addSystemMsg(`⚠ ${msg.text}`);
        break;

      case "tool_result":
        setToolResult(msg.result);
        setToolLoading(false);
        break;
    }
  }, []);

  const { send } = useWebSocket(onWsMessage);

  /* ── 面板切换 ── */
  const handlePanelSelect = useCallback((view: PanelView) => {
    setActivePanel(view);
    setShowNewConv(false);
    setNewConvPreset(null);
  }, []);

  /* ── 发起新对话 ── */
  const handleStartNewConversation = useCallback(
    (partner: string, player: string) => {
      const id = `conv_${Date.now()}`;
      const newConv: Conversation = {
        id, partner, playerCharacter: player,
        title: `${partner} · 扮演${player}`,
        messages: [], createdAt: Date.now(),
      };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(id);
      setShowNewConv(false);
      setActivePanel("chat");
      send({ type: "join", character: player, partner });
    },
    [send]
  );

  const openNewConversation = useCallback((presetPartner?: string) => {
    setNewConvPreset(presetPartner ?? null);
    setShowNewConv(true);
  }, []);

  const cancelNewConversation = useCallback(() => {
    setShowNewConv(false);
    setNewConvPreset(null);
  }, []);

  /* ── 群聊 ── */
  const handleStartGroupChat = useCallback(() => {
    openNewConversation("聊天室");
  }, [openNewConversation]);

  /* ── 切换对话 ── */
  const switchConversation = useCallback(
    (convId: string) => {
      if (convId === activeConvIdRef.current) return;
      setConversations((prev) => {
        const conv = prev.find((c) => c.id === convId);
        if (conv && conv.playerCharacter !== myCharRef.current) {
          pendingRestoreRef.current = [...conv.messages];
          send({ type: "join", character: conv.playerCharacter, partner: conv.partner });
        }
        return prev;
      });
      setActiveConvId(convId);
    },
    [send]
  );

  /* ── 重命名 ── */
  const handleRenameChat = useCallback((convId: string, title: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === convId ? { ...c, title } : c))
    );
  }, []);

  const handleDeleteChat = useCallback((convId: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (activeConvIdRef.current === convId) {
      setActiveConvId(null);
    }
  }, []);

  /* ── 消息 ── */
  const handleSend = useCallback(
    (text: string) => {
      if (!myCharRef.current) return;
      send({ type: "message", text });
    },
    [send]
  );

  const handleStylize = useCallback(
    (text: string) => {
      if (!myCharRef.current) return;
      setIsStylizing(true);
      setStylizeResult(null);
      send({ type: "stylize", text });
    },
    [send]
  );

  const handleClearMessages = useCallback(() => {
    const id = activeConvIdRef.current;
    if (!id) return;
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, messages: [] } : c))
    );
  }, []);

  /* ── 联系人 ── */
  const handleSelectContact = useCallback((name: string) => {
    setSelectedContact(name);
  }, []);

  const handleStartChatFromContact = useCallback(() => {
    if (selectedContact) openNewConversation(selectedContact);
  }, [selectedContact, openNewConversation]);

  /* ── 设置 ── */
  const handleSaveConfig = useCallback(
    (data: {
      apiKey: string; apiUrl: string; model: string;
      characterConfig: Record<string, { api_url: string; model: string }>;
    }) => {
      send({
        type: "set_config", api_key: data.apiKey,
        api_url: data.apiUrl, model: data.model,
        character_config: data.characterConfig,
      });
      fetch("/api/save-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: data.apiKey || undefined,
          api_url: data.apiUrl || undefined,
          model: data.model || undefined,
        }),
      }).catch(() => {});
    },
    [send]
  );

  /* ── 工具 ── */
  const handleToolSelect = useCallback((id: string) => {
    setSelectedTool(id); setToolDraft(""); setToolResult(""); setToolLoading(false);
  }, []);
  const handleToolBack = useCallback(() => {
    setSelectedTool(null); setToolDraft(""); setToolResult(""); setToolLoading(false);
  }, []);
  const handleToolSubmit = useCallback(() => {
    if (!selectedTool || !toolDraft.trim()) return;
    setToolLoading(true); setToolResult("");
    send({ type: "tool_invoke", tool_id: selectedTool, content: toolDraft.trim() });
  }, [selectedTool, toolDraft, send]);
  const handleToolRetry = useCallback(() => {
    setToolResult(""); setToolDraft(""); setToolLoading(false);
  }, []);

  /* ───────────────────────────────────────
     渲染：右侧面板
     ─────────────────────────────────────── */

  function renderRightPanel() {
    if (showNewConv) {
      return <NewConversationView onStart={handleStartNewConversation} onCancel={cancelNewConversation} presetPartner={newConvPreset} />;
    }

    switch (activePanel) {
      case "chat": {
        if (!activeConv) {
          return (
            <div className="flex-1 flex items-center justify-center text-black/20 bg-white/30">
              <div className="text-center">
                <div className="text-3xl mb-3">💬</div>
                <div className="text-sm">还没有对话</div>
                <div className="text-xs mt-2 text-black/15">
                  点击「联系人」或聊天列表上方的 + 开始新对话
                </div>
              </div>
            </div>
          );
        }
        return (
          <>
            <ChatHeader characterName={partnerName} messageCount={messages.length} onClear={handleClearMessages} />
            <ChatArea messages={messages} myCharacter={myCharacter} thinkingCharacters={thinkingCharacters} />
            {myCharacter ? (
              <InputArea myCharacter={myCharacter} connected={isConnected} onSend={handleSend}
                onStylize={handleStylize} stylizeResult={stylizeResult} isStylizing={isStylizing} />
            ) : (
              <div className="px-4 py-3 border-t border-black/5 bg-white/40">
                <div className="text-[11px] text-black/30 text-center">对话准备就绪，等待角色确认...</div>
              </div>
            )}
          </>
        );
      }

      case "contacts": {
        if (!selectedContact) {
          return (
            <div className="flex-1 flex items-center justify-center text-black/20 bg-white/30">
              <div className="text-center"><div className="text-3xl mb-3">👥</div>
                <div className="text-sm">选择一个联系人查看介绍</div>
              </div>
            </div>
          );
        }
        return <ContactDetail characterName={selectedContact} onStartChat={handleStartChatFromContact} />;
      }

      case "tools": {
        const info = selectedTool ? TOOL_DESC[selectedTool] : null;
        if (!info) {
          return (
            <div className="flex-1 flex items-center justify-center text-black/20 bg-white/30">
              <div className="text-center"><div className="text-3xl mb-3">🛠</div><div className="text-sm">选择一个工具</div></div>
            </div>
          );
        }
        return (
          <div className="flex-1 flex flex-col min-w-0 bg-white/30">
            <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
              <div className="flex items-center gap-2.5">
                <button onClick={handleToolBack} className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">← 返回</button>
                <span className="text-black/20">|</span>
                <span className="text-lg leading-none">{info.icon}</span>
                <h2 className="text-sm font-semibold text-[#2c2c2c]">{info.name}</h2>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5 max-w-2xl mx-auto w-full">
              {toolResult ? (
                <><div className="mb-4"><div className="text-xs text-black/30 mb-1.5 font-medium">你的输入</div>
                  <div className="bg-white/80 border border-black/5 rounded-xl px-4 py-3 text-sm text-[#2c2c2c]/70 whitespace-pre-wrap leading-relaxed">{toolDraft}</div></div>
                  <div><div className="text-xs text-black/30 mb-1.5 font-medium">结果</div>
                    {toolLoading ? (
                      <div className="bg-white/80 border border-black/5 rounded-xl px-4 py-12 flex flex-col items-center gap-2">
                        <span className="inline-block w-6 h-6 border-2 border-purple-200 border-t-purple-600 rounded-full animate-spin" />
                        <span className="text-xs text-black/30">分析中...</span>
                      </div>
                    ) : (
                      <div className="bg-white border border-black/5 rounded-xl px-4 py-4 text-sm text-[#2c2c2c]/80 whitespace-pre-wrap leading-relaxed">{toolResult}</div>
                    )}</div></>
              ) : (
                <><p className="text-sm text-black/40 mb-4">{info.desc}</p>
                  <textarea value={toolDraft} onChange={(e) => setToolDraft(e.target.value)}
                    placeholder={info.placeholder} rows={8}
                    className="w-full bg-white border border-black/10 rounded-xl px-4 py-3 text-sm resize-none focus:border-purple-400 focus:outline-none placeholder-black/20" /></>
              )}
            </div>
            <div className="px-6 py-3 border-t border-black/5 bg-white/60 shrink-0 max-w-2xl mx-auto w-full flex justify-end gap-2">
              {toolResult && !toolLoading ? (
                <><button onClick={handleToolRetry} className="text-xs bg-black/5 hover:bg-black/10 text-black/50 px-3 py-1.5 rounded-lg font-medium transition">重新输入</button>
                  <button onClick={handleToolSubmit} className="text-xs bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg font-medium transition">再次分析</button></>
              ) : (
                <button onClick={handleToolSubmit} disabled={!toolDraft.trim() || toolLoading}
                  className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300 text-white px-5 py-2 rounded-lg text-sm font-medium transition">
                  {toolLoading ? "分析中..." : "分析"}
                </button>
              )}
            </div>
          </div>
        );
      }

      case "history":
        return (
          <div className="flex-1 flex items-center justify-center text-black/20 bg-white/30">
            <div className="text-center"><div className="text-3xl mb-3">📁</div><div className="text-sm">对话历史</div>
              <div className="text-xs mt-1 text-black/15">SQLite 持久化后可用</div></div>
          </div>
        );
    }
  }

  return (
    <div className="h-screen flex bg-white/40">
      <IconBar activeView={activePanel} onSelect={handlePanelSelect} onSettings={() => setSettingsOpen(true)} />

      <MiddlePanel
        activePanel={activePanel}
        conversations={conversations}
        activeConvId={activeConvId}
        selectedContact={selectedContact}
        selectedTool={selectedTool}
        onSelectChat={switchConversation}
        onSelectContact={handleSelectContact}
        onSelectTool={handleToolSelect}
        onNewChat={() => openNewConversation()}
        onStartGroupChat={handleStartGroupChat}
        onRenameChat={handleRenameChat}
        onDeleteChat={handleDeleteChat}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {renderRightPanel()}
      </div>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)}
        onSave={handleSaveConfig} hasApiKey={config.hasApiKey}
        initialApiUrl={config.apiUrl} initialModel={config.model} />
    </div>
  );
}
