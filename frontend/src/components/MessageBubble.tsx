import { getCharacter } from "../characters";
import type { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const char = getCharacter(message.character);
  const isBot = message.isBot;

  return (
    <div className={`flex items-start gap-2 ${isBot ? "" : "flex-row-reverse"}`}>
      {/* Avatar */}
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 mt-0.5"
        style={{ background: `${char.color}15` }}
      >
        {char.emoji}
      </div>

      {/* Bubble */}
      <div
        className={`
          max-w-[70%] rounded-2xl px-3.5 py-2
          ${isBot
            ? "bg-white shadow-sm border border-black/5 rounded-bl-md"
            : "bg-purple-50 border border-purple-100 rounded-br-md"
          }
        `}
      >
        <div
          className="text-xs font-medium mb-0.5"
          style={{ color: char.color }}
        >
          {message.character}
        </div>
        <div className="text-sm leading-relaxed text-[#2c2c2c]/80 whitespace-pre-wrap break-words">
          {message.text}
        </div>
      </div>
    </div>
  );
}
