import { useState, useRef, useEffect } from "react";

interface InputAreaProps {
  myCharacter: string | null;
  connected: boolean;
  onSend: (text: string) => void;
  onStyleTransfer: (text: string) => void;
  transformedText: string | null;
  onSendStyled: (text: string) => void;
  onCancelStyle: () => void;
  styleLoading: boolean;
}

export default function InputArea({
  myCharacter,
  connected,
  onSend,
  onStyleTransfer,
  transformedText,
  onSendStyled,
  onCancelStyle,
  styleLoading,
}: InputAreaProps) {
  const [text, setText] = useState("");
  const [editableStyled, setEditableStyled] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (transformedText) {
      setEditableStyled(transformedText);
    }
  }, [transformedText]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [text]);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const disabled = !myCharacter || !connected;

  return (
    <div className="px-4 py-2.5 border-t border-black/5 bg-white/70 backdrop-blur-sm">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              !myCharacter
                ? "先在左侧选择角色..."
                : `以 ${myCharacter} 的身份发言...`
            }
            disabled={disabled}
            className="w-full bg-white/80 text-[#2c2c2c] rounded-xl px-4 py-2.5 text-sm
                       border border-black/10 focus:border-purple-400 focus:outline-none
                       resize-none placeholder-black/20 shadow-sm
                       disabled:opacity-40"
          />

          {/* Style preview area */}
          {transformedText && (
            <div className="mt-1.5 bg-purple-50 border border-purple-200 rounded-lg p-2">
              <textarea
                value={editableStyled}
                onChange={(e) => setEditableStyled(e.target.value)}
                rows={2}
                className="w-full bg-transparent text-sm text-[#2c2c2c] resize-none
                           border-none focus:outline-none"
              />
              <div className="flex items-center justify-end gap-1.5 mt-1">
                <button
                  onClick={() => onSendStyled(editableStyled)}
                  className="bg-purple-600 hover:bg-purple-500 text-white text-xs px-3 py-1.5 rounded-lg transition"
                >
                  发送此版本
                </button>
                <button
                  onClick={onCancelStyle}
                  className="text-black/40 hover:text-black/60 text-xs px-3 py-1.5 rounded-lg transition"
                >
                  取消
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-1 shrink-0 pb-0.5">
          <button
            onClick={() => {
              const trimmed = text.trim();
              if (trimmed) onStyleTransfer(trimmed);
            }}
            disabled={disabled || !text.trim() || styleLoading}
            className="relative bg-white/80 border border-black/10 hover:bg-purple-50 hover:border-purple-300
                       text-black/50 hover:text-purple-600 px-3 py-2.5 rounded-xl text-xs font-medium
                       transition disabled:opacity-30 disabled:cursor-not-allowed overflow-hidden"
          >
            {styleLoading && (
              <span
                className="absolute inset-0 bg-purple-200 animate-pulse"
                style={{ width: "60%" }}
              />
            )}
            <span className="relative z-10">
              {styleLoading ? "转化中..." : "风格化"}
            </span>
          </button>
          <button
            onClick={handleSend}
            disabled={disabled || !text.trim()}
            className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300
                       text-white px-4 py-2.5 rounded-xl text-sm font-medium
                       transition shadow-sm disabled:shadow-none disabled:cursor-not-allowed"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
}
