import { useState } from "react";
import type { PanelView, Conversation } from "../types";
import { CHARACTERS } from "../characters";
import { ALL_TOOLS } from "../tools/registry";
import { isToolEnabled } from "../tools/preferences";

/* ───────────────────────────────────────────
   Props
   ─────────────────────────────────────────── */

interface MiddlePanelProps {
  activePanel: PanelView;
  conversations: Conversation[];
  activeConvId: string | null;
  selectedContact: string | null;
  selectedTool: string | null;
  onSelectChat: (convId: string) => void;
  onSelectContact: (name: string) => void;
  onSelectTool: (id: string) => void;
  onNewChat: () => void;
  onStartGroupChat: () => void;
  onRenameChat: (convId: string, title: string) => void;
  onDeleteChat: (convId: string) => void;
}

/* ───────────────────────────────────────────
   Chat List
   ─────────────────────────────────────────── */

function ChatListView({
  conversations,
  activeConvId,
  onSelectChat,
  onRenameChat,
  onDeleteChat,
  onNewChat,
}: {
  conversations: Conversation[];
  activeConvId: string | null;
  onSelectChat: (convId: string) => void;
  onRenameChat: (convId: string, title: string) => void;
  onDeleteChat: (convId: string) => void;
  onNewChat: () => void;
}) {
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");

  const startRename = (convId: string, current: string) => {
    setRenaming(convId);
    setRenameDraft(current);
  };

  const commitRename = () => {
    if (renaming && renameDraft.trim()) {
      onRenameChat(renaming, renameDraft.trim());
    }
    setRenaming(null);
  };

  // 空状态
  if (conversations.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-3 py-2.5 border-b border-black/5 flex items-center justify-between shrink-0">
          <span className="text-sm font-semibold text-[#2c2c2c]">聊天</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-black/20 px-6">
          <div className="text-2xl mb-2">💬</div>
          <div className="text-xs text-center">还没有对话</div>
          <div className="text-[11px] text-black/15 mt-1 text-center">
            点击上方 + 或通过联系人发起新对话
          </div>
        </div>
      </div>
    );
  }

  // partner → emoji 查找
  function partnerEmoji(name: string): string {
    return CHARACTERS.find((c) => c.name === name)?.emoji ?? "❓";
  }
  function partnerColor(name: string): string {
    return CHARACTERS.find((c) => c.name === name)?.color ?? "#888";
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-black/5 flex items-center justify-between shrink-0">
        <span className="text-sm font-semibold text-[#2c2c2c]">聊天</span>
        <button
          onClick={onNewChat}
          className="w-7 h-7 rounded-lg bg-purple-100 hover:bg-purple-200 text-purple-600
                     flex items-center justify-center text-lg leading-none transition"
          title="新建对话"
        >
          +
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {conversations.map((conv) => {
          const isActive = activeConvId === conv.id;
          const isRenaming = renaming === conv.id;

          return (
            <div
              key={conv.id}
              className={`
                group flex items-center gap-2.5 px-3 py-2.5 mx-1 rounded-lg cursor-pointer
                transition-all duration-150
                ${isActive ? "bg-purple-50" : "hover:bg-black/4"}
              `}
              onClick={() => !isRenaming && onSelectChat(conv.id)}
            >
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0"
                style={{ background: `${partnerColor(conv.partner)}18` }}
              >
                {partnerEmoji(conv.partner)}
              </div>
              <div className="flex-1 min-w-0">
                {isRenaming ? (
                  <input
                    autoFocus
                    value={renameDraft}
                    onChange={(e) => setRenameDraft(e.target.value)}
                    onBlur={commitRename}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename();
                      if (e.key === "Escape") setRenaming(null);
                    }}
                    className="w-full text-sm border-b border-purple-400 bg-transparent
                               outline-none text-[#2c2c2c] py-0"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-[#2c2c2c] truncate">
                      {conv.title}
                    </span>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition shrink-0 ml-1">
                      <button onClick={(e) => { e.stopPropagation(); startRename(conv.id, conv.title); }}
                        className="text-[11px] text-black/30 hover:text-purple-500 px-1" title="重命名">✏️</button>
                      <button onClick={(e) => { e.stopPropagation(); onDeleteChat(conv.id); }}
                        className="text-[11px] text-black/30 hover:text-red-500 px-1" title="删除">✕</button>
                    </div>
                  </div>
                )}
                <div className="text-xs text-black/35 truncate mt-0.5">
                  {conv.messages.length > 0
                    ? conv.messages[conv.messages.length - 1].text.slice(0, 20) + (conv.messages[conv.messages.length - 1].text.length > 20 ? "..." : "")
                    : ""}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ───────────────────────────────────────────
   Contact List
   ─────────────────────────────────────────── */

function ContactListView({
  selectedContact,
  onSelectContact,
  onStartGroupChat,
}: {
  selectedContact: string | null;
  onSelectContact: (name: string) => void;
  onStartGroupChat: () => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-black/5 shrink-0">
        <span className="text-sm font-semibold text-[#2c2c2c]">联系人</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-3 py-2 text-[11px] text-black/30 font-medium tracking-wider uppercase">个人</div>
        <div className="px-2">
          {CHARACTERS.map((c) => {
            const isActive = selectedContact === c.name;
            return (
              <div
                key={c.name}
                onClick={() => onSelectContact(c.name)}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150
                  ${isActive ? "bg-purple-50 ring-1 ring-purple-200" : "hover:bg-black/4"}
                `}
              >
                <div className="w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0"
                  style={{ background: `${c.color}18` }}>
                  {c.emoji}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-[#2c2c2c]">{c.name}</div>
                  <div className="text-xs mt-0.5 truncate" style={{ color: `${c.color}99` }}>{c.title}</div>
                </div>
                {isActive && <span className="w-2 h-2 rounded-full bg-purple-400 shrink-0" />}
              </div>
            );
          })}
        </div>

        <div className="mt-3">
          <div className="px-3 py-2 text-[11px] text-black/30 font-medium tracking-wider uppercase">群聊</div>
          <div className="px-2 pb-2">
            <div onClick={onStartGroupChat}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer hover:bg-black/4 transition-all duration-150">
              <div className="w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0 bg-gradient-to-br from-purple-100 to-pink-100">
                🏠
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[#2c2c2c]">SOS团聊天室</div>
                <div className="text-xs text-black/35 mt-0.5 truncate">全员群聊</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────────────────────────
   Tool List
   ─────────────────────────────────────────── */

// 工具列表自动发现自 tools/ 目录，按启用状态过滤
const TOOL_LIST = ALL_TOOLS
  .filter((t) => isToolEnabled(t.id))
  .map((t) => ({ id: t.id, icon: t.icon, name: t.name }));

function ToolListView({ selectedTool, onSelectTool }: {
  selectedTool: string | null;
  onSelectTool: (id: string) => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-black/5 shrink-0">
        <span className="text-sm font-semibold text-[#2c2c2c]">春日工具包</span>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {TOOL_LIST.map((t) => (
          <button key={t.id} onClick={() => onSelectTool(t.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-left transition-all duration-150
              ${selectedTool === t.id ? "bg-purple-50 text-purple-700 ring-1 ring-purple-200" : "text-black/60 hover:bg-black/4"}`}>
            <span className="text-lg">{t.icon}</span>
            <span className="font-medium">{t.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────────────────────────────
   History List
   ─────────────────────────────────────────── */

function HistoryListView() {
  return (
    <div className="flex flex-col h-full items-center justify-center text-black/20 px-4">
      <div className="text-2xl mb-2">📁</div>
      <div className="text-xs text-center">对话历史</div>
      <div className="text-[11px] text-black/15 mt-1 text-center">SQLite 持久化后可用</div>
    </div>
  );
}

/* ───────────────────────────────────────────
   MiddlePanel
   ─────────────────────────────────────────── */

export default function MiddlePanel({
  activePanel,
  conversations,
  activeConvId,
  selectedContact,
  selectedTool,
  onSelectChat,
  onSelectContact,
  onSelectTool,
  onNewChat,
  onStartGroupChat,
  onRenameChat,
  onDeleteChat,
}: MiddlePanelProps) {
  return (
    <div className="w-[280px] bg-white/75 backdrop-blur-sm border-r border-black/5 flex flex-col shrink-0">
      {activePanel === "chat" && (
        <ChatListView conversations={conversations} activeConvId={activeConvId}
          onSelectChat={onSelectChat} onRenameChat={onRenameChat} onDeleteChat={onDeleteChat} onNewChat={onNewChat} />
      )}
      {activePanel === "contacts" && (
        <ContactListView selectedContact={selectedContact}
          onSelectContact={onSelectContact} onStartGroupChat={onStartGroupChat} />
      )}
      {activePanel === "tools" && (
        <ToolListView selectedTool={selectedTool} onSelectTool={onSelectTool} />
      )}
      {activePanel === "history" && <HistoryListView />}
    </div>
  );
}
