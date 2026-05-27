import { useEffect, useRef } from "react";
import type { Message } from "../types";
import MessageBubble from "./MessageBubble";
import { getCharacter } from "../characters";

interface ChatAreaProps {
  messages: Message[];
  myCharacter: string | null;
  thinkingCharacters: string[];
}

export default function ChatArea({ messages, myCharacter, thinkingCharacters }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-black/20">
        <div className="text-center">
          <div className="text-3xl mb-3">🌌</div>
          <div className="text-sm">SOS团聊天室</div>
          <div className="text-xs mt-1 text-black/15">
            {myCharacter
              ? `以 ${myCharacter} 的身份发言吧`
              : "选择角色开始对话"}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2.5">
      {messages.map((msg) => (
        <div key={msg.id} className="animate-[fadeIn_0.3s_ease]">
          {msg.character === "__system__" ? (
            <div className="text-center py-1">
              <span className="text-black/25 text-xs">{msg.text}</span>
            </div>
          ) : (
            <MessageBubble message={msg} />
          )}
        </div>
      ))}

      {/* Thinking indicators */}
      {thinkingCharacters.map((char) => {
        const info = getCharacter(char);
        return (
          <div key={`thinking-${char}`} className="flex items-start gap-2">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 mt-0.5"
              style={{ background: `${info.color}15` }}
            >
              {info.emoji}
            </div>
            <div className="flex items-center gap-2 text-sm text-black/30">
              <span className="font-medium" style={{ color: info.color }}>
                {char}
              </span>
              <span className="italic animate-pulse">思考中…</span>
            </div>
          </div>
        );
      })}

      <div ref={bottomRef} />
    </div>
  );
}
