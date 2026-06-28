import { useState, useRef, useEffect, useCallback } from "react";

interface StylizeResult {
  original: string;
  transformed: string | null;
  already_in_character: boolean;
  message: string;
  score?: number;
}

interface PreviewInfo {
  original: string;
  transformed: string | null;
  already_in_character: boolean;
  message: string;
  score: number;
}

interface InputAreaProps {
  myCharacter: string | null;
  connected: boolean;
  onSend: (text: string) => void;
  onStylize: (text: string) => void;
  stylizeResult: StylizeResult | null;
  isStylizing: boolean;
}

type StyleState = "idle" | "stylizing" | "preview";

export default function InputArea({
  myCharacter,
  connected,
  onSend,
  onStylize,
  stylizeResult,
  isStylizing,
}: InputAreaProps) {
  const [text, setText] = useState("");
  const [styleState, setStyleState] = useState<StyleState>("idle");
  const [preview, setPreview] = useState<PreviewInfo | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const textRef = useRef(text);
  textRef.current = text;
  const pendingOriginalRef = useRef<string | null>(null);
  const processedRef = useRef<string | null>(null);

  // Consume stylizeResult from parent
  useEffect(() => {
    if (!stylizeResult) return;
    if (stylizeResult.original !== pendingOriginalRef.current) return;
    if (stylizeResult.original === processedRef.current) return;

    processedRef.current = stylizeResult.original;
    pendingOriginalRef.current = null;
    setErrorMsg("");

    if (stylizeResult.already_in_character) {
      setPreview({
        original: stylizeResult.original,
        transformed: null,
        already_in_character: true,
        message: stylizeResult.message,
        score: stylizeResult.score ?? 0,
      });
      setStyleState("preview");
    } else if (stylizeResult.transformed) {
      setPreview({
        original: stylizeResult.original,
        transformed: stylizeResult.transformed,
        already_in_character: false,
        message: stylizeResult.message,
        score: stylizeResult.score ?? 0,
      });
      setStyleState("preview");
    } else {
      setErrorMsg("风格化失败，请重试");
    }
  }, [stylizeResult]);

  // Reset on character switch
  useEffect(() => {
    setText("");
    setStyleState("idle");
    setPreview(null);
    setErrorMsg("");
    pendingOriginalRef.current = null;
    processedRef.current = null;
  }, [myCharacter]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [text]);

  const dismissPreview = useCallback(() => {
    setStyleState("idle");
    setPreview(null);
  }, []);

  const cancelPending = useCallback(() => {
    pendingOriginalRef.current = null;
  }, []);

  const triggerStylize = useCallback((inputText: string) => {
    pendingOriginalRef.current = inputText;
    processedRef.current = null;
    setStyleState("stylizing");
    setPreview(null);
    setErrorMsg("");
    onStylize(inputText);
  }, [onStylize]);

  const sendAndClear = useCallback((sendText: string) => {
    cancelPending();
    onSend(sendText);
    setText("");
    setStyleState("idle");
    setPreview(null);
    setErrorMsg("");
  }, [onSend, cancelPending]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    setErrorMsg("");
    if (styleState === "stylizing" || styleState === "preview") {
      // Editing during stylizing → cancel pending result
      // Editing during preview → preview is now outdated
      cancelPending();
      dismissPreview();
    }
  }, [styleState, cancelPending, dismissPreview]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    const trimmed = textRef.current.trim();

    // Ctrl/Cmd + Enter → always send original text, clear all
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (!trimmed) return;
      sendAndClear(trimmed);
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!trimmed) return;

      // stylizing → Enter ignored (wait for result)
      if (styleState === "stylizing") return;

      // preview → send stylized if text unchanged, else re-stylize
      if (styleState === "preview" && preview) {
        if (trimmed === preview.original) {
          sendAndClear(preview.transformed ?? preview.original);
          return;
        }
        // Text has changed from the stylized original → start new stylization
        triggerStylize(trimmed);
        return;
      }

      // idle → start stylization
      triggerStylize(trimmed);
    }

    if (e.key === "Escape" && styleState === "preview") {
      e.preventDefault();
      dismissPreview();
    }
  }, [styleState, preview, sendAndClear, triggerStylize, dismissPreview]);

  const handleSendPreview = useCallback(() => {
    if (!preview) return;
    sendAndClear(preview.transformed ?? preview.original);
  }, [preview, sendAndClear]);

  const handleSendOriginal = useCallback(() => {
    sendAndClear(textRef.current.trim() || (preview?.original ?? ""));
  }, [sendAndClear, preview]);

  const handleButtonClick = useCallback(() => {
    const trimmed = textRef.current.trim();
    if (!trimmed || styleState === "stylizing") return;

    if (styleState === "preview" && preview && trimmed === preview.original) {
      sendAndClear(preview.transformed ?? preview.original);
      return;
    }

    triggerStylize(trimmed);
  }, [styleState, preview, sendAndClear, triggerStylize]);

  const disabled = !myCharacter || !connected;

  return (
    <div className="px-4 py-2.5 border-t border-black/5 bg-white/70 backdrop-blur-sm">
      {/* ── Preview Panel ── */}
      {preview && (
        <div className="mb-2 bg-purple-50/80 backdrop-blur-sm border border-purple-200/50 rounded-xl p-3">
          {/* Header: status + close */}
          <div className="flex items-start justify-between mb-1.5">
            <div className="flex items-center gap-2 flex-wrap min-w-0">
              {preview.already_in_character ? (
                <span className="text-green-600 text-xs font-medium">
                  {preview.message}
                </span>
              ) : (
                <span className="text-purple-600 text-xs font-medium">
                  风格化预览
                </span>
              )}
              {preview.score > 0 && (
                <span className="text-[10px] text-black/30 whitespace-nowrap">
                  原匹配度: {Math.round(preview.score * 100)}%
                </span>
              )}
              {!preview.already_in_character && preview.message && (
                <span className="text-[10px] text-black/25 truncate">
                  {preview.message}
                </span>
              )}
            </div>
            <button
              onClick={dismissPreview}
              className="text-black/20 hover:text-black/50 text-sm leading-none shrink-0 ml-2"
            >
              ✕
            </button>
          </div>

          {/* Stylized text (only when transformed) */}
          {!preview.already_in_character && preview.transformed && (
            <div className="bg-white rounded-lg px-3 py-2 text-sm text-[#2c2c2c] mb-2.5 border border-purple-100/50">
              {preview.transformed}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-1.5 justify-end items-center">
            <span className="text-[10px] text-black/20 mr-auto">
              Enter 发送 &middot; Ctrl+Enter 原文 &middot; Esc 关闭
            </span>
            {!preview.already_in_character && (
              <button
                onClick={handleSendOriginal}
                className="text-[11px] bg-white hover:bg-black/5 text-black/40 px-2.5 py-1.5 rounded-lg border border-black/10 transition"
              >
                发送原文
              </button>
            )}
            <button
              onClick={handleSendPreview}
              className={`text-[11px] font-medium px-3 py-1.5 rounded-lg transition ${
                preview.already_in_character
                  ? "bg-green-500 hover:bg-green-400 text-white"
                  : "bg-purple-600 hover:bg-purple-500 text-white"
              }`}
            >
              {preview.already_in_character ? "发送原文" : "发送风格化版本"}
            </button>
          </div>
        </div>
      )}

      {/* ── Error Message ── */}
      {errorMsg && (
        <div className="mb-2 text-red-500 text-xs bg-red-50/50 rounded-lg px-3 py-2">
          {errorMsg}
        </div>
      )}

      {/* ── Input Row ── */}
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
            className={`w-full bg-white/80 text-[#2c2c2c] rounded-xl px-4 py-2.5 text-sm
                       border focus:outline-none resize-none placeholder-black/20 shadow-sm
                       disabled:opacity-40 transition-colors duration-150 ${
                         styleState === "stylizing"
                           ? "border-purple-300 focus:border-purple-400"
                           : "border-black/10 focus:border-purple-400"
                       }`}
          />

          {/* Stylizing indicator */}
          {styleState === "stylizing" && (
            <div className="mt-1.5 flex items-center min-h-[20px]">
              <span className="text-purple-500 text-xs flex items-center gap-1">
                <span className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
                风格化中…
                <span className="text-black/20 ml-1">Ctrl+Enter 直接发原文</span>
              </span>
            </div>
          )}
        </div>

        <button
          onClick={handleButtonClick}
          disabled={disabled || !text.trim() || styleState === "stylizing"}
          className={`
            px-5 py-2.5 rounded-xl text-sm font-medium transition shrink-0
            shadow-sm disabled:shadow-none disabled:cursor-not-allowed
            ${styleState === "preview"
              ? "bg-purple-600 hover:bg-purple-500 text-white"
              : "bg-black/5 hover:bg-black/10 text-black/50"
            }
            disabled:opacity-30
          `}
        >
          {styleState === "preview" ? "发送" : "风格化 →"}
        </button>
      </div>
    </div>
  );
}
