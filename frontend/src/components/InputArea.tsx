import { useState, useRef, useEffect, useCallback } from "react";

type StyleState = "idle" | "stylizing" | "stylized" | "already_character";

interface StylizeResult {
  original: string;
  transformed: string | null;
  already_in_character: boolean;
  message: string;
  score?: number;
}

interface InputAreaProps {
  myCharacter: string | null;
  connected: boolean;
  onSend: (text: string) => void;
  onStylize: (text: string) => void;
  stylizeResult: StylizeResult | null;
  isStylizing: boolean;
}

export default function InputArea({
  myCharacter,
  connected,
  onSend,
  onStylize,
  stylizeResult,
  isStylizing,
}: InputAreaProps) {
  const [text, setText] = useState("");
  const [originalText, setOriginalText] = useState("");
  const [styleState, setStyleState] = useState<StyleState>("idle");
  const [styleMessage, setStyleMessage] = useState("");
  const [styleScore, setStyleScore] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const textRef = useRef(text);
  textRef.current = text;

  // 监听父组件传来的风格化结果
  useEffect(() => {
    if (!stylizeResult) return;
    if (stylizeResult.original !== text && stylizeResult.original !== originalText) return;

    setStyleScore(stylizeResult.score ?? 0);

    if (stylizeResult.already_in_character) {
      setStyleState("already_character");
      setStyleMessage(stylizeResult.message);
    } else if (stylizeResult.transformed) {
      setText(stylizeResult.transformed);
      setStyleState("stylized");
      setStyleMessage(stylizeResult.message);
    }
  }, [stylizeResult]);

  // 重置状态（角色切换时）
  useEffect(() => {
    setText("");
    setStyleState("idle");
    setStyleMessage("");
    setStyleScore(0);
  }, [myCharacter]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [text]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    if (styleState === "stylized" || styleState === "already_character") {
      setStyleState("idle");
      setStyleMessage("");
      setStyleScore(0);
    }
  }, [styleState]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const trimmed = textRef.current.trim();
      if (!trimmed) return;
      if (isStylizing) return;

      if (styleState === "stylized" || styleState === "already_character") {
        onSend(trimmed);
        setText("");
        setStyleState("idle");
        setStyleMessage("");
        setStyleScore(0);
        return;
      }

      // 未风格化 → 请求风格化
      setOriginalText(trimmed);
      setStyleState("stylizing");
      setStyleMessage("风格化中…");
      setStyleScore(0);
      onStylize(trimmed);
    }

    if (e.key === "Escape" && styleState === "stylized") {
      e.preventDefault();
      setText(originalText);
      setStyleState("already_character");  // 按Esc还原后，Enter直接发送
      setStyleMessage("已还原原文，Enter 直接发送");
      setStyleScore(0);
    }
  }, [styleState, isStylizing, originalText, onSend, onStylize]);

  const handleReStylize = useCallback(() => {
    const trimmed = textRef.current.trim();
    if (!trimmed) return;
    setOriginalText(trimmed);
    setStyleState("stylizing");
    setStyleMessage("风格化中…");
    setStyleScore(0);
    onStylize(trimmed);
  }, [onStylize]);

  const disabled = !myCharacter || !connected;

  const statusTag = () => {
    if (styleState === "stylizing") {
      return (
        <span className="text-purple-500 text-xs flex items-center gap-1">
          <span className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
          风格化中
        </span>
      );
    }
    if (styleState === "stylized") {
      return (
        <div className="flex items-center gap-2">
          <span className="text-purple-500 text-xs">✨ 已风格化</span>
          <span className="text-[10px] text-black/25">Esc 还原 / Enter 发送</span>
          {styleScore > 0 && (
            <span className="text-[10px] text-black/30">
              原角色匹配度: {Math.round(styleScore * 100)}%
            </span>
          )}
        </div>
      );
    }
    if (styleState === "already_character") {
      return (
        <div className="flex items-center gap-2">
          <span className="text-green-500 text-xs">{styleMessage}</span>
          <span className="text-[10px] text-black/25">Enter 直接发送</span>
          {styleScore > 0 && (
            <span className="text-[10px] text-black/30">
              匹配度: {Math.round(styleScore * 100)}%
            </span>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="px-4 py-2.5 border-t border-black/5 bg-white/70 backdrop-blur-sm">
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleChange}
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
                       disabled:opacity-40 transition-colors duration-150"
          />

          {/* 状态指示器 */}
          {(styleState !== "idle" || isStylizing) && (
            <div className="mt-1.5 flex items-center min-h-[20px]">
              {statusTag()}
            </div>
          )}
        </div>

        <button
          onClick={() => {
            const trimmed = text.trim();
            if (!trimmed || isStylizing) return;
            if (styleState === "stylized" || styleState === "already_character") {
              onSend(trimmed);
              setText("");
              setStyleState("idle");
              setStyleMessage("");
              setStyleScore(0);
              return;
            }
            setOriginalText(trimmed);
            setStyleState("stylizing");
            setStyleMessage("风格化中…");
            setStyleScore(0);
            onStylize(trimmed);
          }}
          disabled={disabled || !text.trim() || isStylizing}
          className={`
            px-5 py-2.5 rounded-xl text-sm font-medium transition shrink-0
            shadow-sm disabled:shadow-none disabled:cursor-not-allowed
            ${styleState === "stylized" || styleState === "already_character"
              ? "bg-purple-600 hover:bg-purple-500 text-white"
              : "bg-black/5 hover:bg-black/10 text-black/50"
            }
            disabled:opacity-30
          `}
        >
          {styleState === "stylized" || styleState === "already_character" ? "发送" : "风格化 →"}
        </button>
      </div>
    </div>
  );
}
