import { useState, useCallback, useRef, useEffect } from "react";
import type { Message, ChatConfig, WsMessage } from "./types";
import { useWebSocket } from "./hooks/useWebSocket";
import Sidebar from "./components/Sidebar";
import ChatArea from "./components/ChatArea";
import InputArea from "./components/InputArea";
import SettingsModal from "./components/SettingsModal";
import ToolPanel from "./components/ToolPanel";

let msgCounter = 0;
function nextId() {
  return `msg_${++msgCounter}`;
}

export default function App() {
  const [myCharacter, setMyCharacter] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [config, setConfig] = useState<ChatConfig>({
    demoMode: true,
    hasApiKey: false,
    apiUrl: "https://api.deepseek.com",
    model: "deepseek-v4-flash",
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [toolLoading, setToolLoading] = useState(false);
  const [toolSession, setToolSession] = useState<{ toolId: string; userInput: string } | null>(null);
  const [toolResult, setToolResult] = useState("");
  const [transformedText, setTransformedText] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [thinkingCharacters, setThinkingCharacters] = useState<string[]>([]);
  const myCharRef = useRef<string | null>(null);

  // 从服务器加载聊天背景
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

  // Keep ref in sync
  myCharRef.current = myCharacter;

  const [styleLoading, setStyleLoading] = useState(false);

  function addSystemMsg(text: string) {
    setMessages((prev) => [
      ...prev,
      { id: nextId(), character: "__system__", text, isBot: false },
    ]);
  }

  const onWsMessage = useCallback((msg: WsMessage) => {
    switch (msg.type) {
      case "config":
        setConfig({
          demoMode: msg.demo_mode,
          hasApiKey: msg.has_api_key,
          apiUrl: msg.api_url,
          model: msg.model,
        });
        setIsConnected(true);
        break;

      case "config_updated":
        setConfig((prev) => ({
          ...prev,
          demoMode: msg.demo_mode,
          hasApiKey: msg.has_api_key,
          apiUrl: msg.api_url,
          model: msg.model,
        }));
        setSettingsOpen(false);
        addSystemMsg(msg.has_api_key ? "配置已保存，AI模式已开启" : "已切换为演示模式");
        break;

      case "character_ready":
        setMyCharacter(msg.character);
        setMessages([]);
        setTransformedText(null);
        addSystemMsg(`你以 ${msg.character} 的身份加入了聊天室`);
        break;

      case "message":
        setMessages((prev) => [
          ...prev,
          { id: nextId(), character: msg.character, text: msg.text, isBot: msg.is_bot },
        ]);
        break;

      case "style_transferred":
        setTransformedText(msg.transformed);
        setStyleLoading(false);
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

  const handleSelectCharacter = useCallback(
    (name: string) => {
      if (name === myCharRef.current) return;
      send({ type: "join", character: name });
    },
    [send]
  );

  const handleSend = useCallback(
    (text: string) => {
      if (!myCharRef.current) return;
      send({ type: "message", text });
    },
    [send]
  );

  const handleStyleTransfer = useCallback(
    (text: string) => {
      if (!myCharRef.current) return;
      setStyleLoading(true);
      send({ type: "style_transfer", text });
    },
    [send]
  );

  const handleSendStyled = useCallback(
    (text: string) => {
      if (!myCharRef.current) return;
      send({ type: "message", text });
      setTransformedText(null);
    },
    [send]
  );

  const handleCancelStyle = useCallback(() => {
    setTransformedText(null);
  }, []);

  const handleSaveConfig = useCallback(
    (data: { apiKey: string; apiUrl: string; model: string; characterConfig: Record<string, {api_url: string; model: string}> }) => {
      send({
        type: "set_config",
        api_key: data.apiKey,
        api_url: data.apiUrl,
        model: data.model,
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

  // ── 工具流程 ──

  const handleToolSelect = useCallback((toolId: string) => {
    setToolSession({ toolId, userInput: "" });
    setToolResult("");
    setToolLoading(false);
  }, []);

  const handleToolSubmit = useCallback(
    (toolId: string, content: string) => {
      setToolLoading(true);
      setToolResult("");
      setToolSession({ toolId, userInput: content });
      send({ type: "tool_invoke", tool_id: toolId, content });
    },
    [send]
  );

  const handleToolBack = useCallback(() => {
    setToolSession(null);
    setToolResult("");
    setToolLoading(false);
  }, []);

  const handleToolRetry = useCallback(() => {
    if (toolSession) {
      setToolResult("");
      setToolSession({ toolId: toolSession.toolId, userInput: "" });
      setToolLoading(false);
    }
  }, [toolSession]);

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-2.5 bg-white/70 backdrop-blur-sm border-b border-black/5 shrink-0">
        <div className="flex items-center gap-2">
          <h1 className="font-bold text-lg text-[#2c2c2c]">SOS团聊天室</h1>
          {config.demoMode && (
            <span className="text-[10px] bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
              演示模式
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSettingsOpen(true)}
            className="text-black/30 hover:text-black/60 transition text-lg px-1"
            title="设置"
          >
            ⚙
          </button>
          <button
            onClick={() => {
              setMessages([]);
              setTransformedText(null);
            }}
            className="text-xs text-black/30 hover:text-black/60 transition px-2.5 py-1 rounded border border-black/10 hover:border-black/20"
          >
            清除对话
          </button>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          currentCharacter={myCharacter}
          onSelect={handleSelectCharacter}
          onToolSelect={handleToolSelect}
        />

        {toolSession ? (
          <ToolPanel
            toolId={toolSession.toolId}
            userInput={toolSession.userInput}
            result={toolResult}
            loading={toolLoading}
            onBack={handleToolBack}
            onSubmit={handleToolSubmit}
            onRetry={handleToolRetry}
          />
        ) : (
          <main className="flex-1 flex flex-col min-w-0">
            <ChatArea messages={messages} myCharacter={myCharacter} thinkingCharacters={thinkingCharacters} />
            <InputArea
              myCharacter={myCharacter}
              connected={isConnected}
              onSend={handleSend}
              onStyleTransfer={handleStyleTransfer}
              transformedText={transformedText}
              onSendStyled={handleSendStyled}
              onCancelStyle={handleCancelStyle}
              styleLoading={styleLoading}
            />
          </main>
        )}
      </div>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSave={handleSaveConfig}
        hasApiKey={config.hasApiKey}
        initialApiUrl={config.apiUrl}
        initialModel={config.model}
      />
    </div>
  );
}
