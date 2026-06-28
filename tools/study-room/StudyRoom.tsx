import { useState, useRef, useEffect, useCallback } from "react";

export default function StudyRoom({ onBack }: { onBack: () => void }) {
  const [bgImage, setBgImage] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [noiseFile, setNoiseFile] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const bgInputRef = useRef<HTMLInputElement>(null);
  const noiseInputRef = useRef<HTMLInputElement>(null);

  // Floating timer state
  const [timerX, setTimerX] = useState(60);
  const [timerY, setTimerY] = useState(120);
  const [fontSize, setFontSize] = useState(64);
  const [fontColor, setFontColor] = useState("#2c2c2c");
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0, startX: 0, startY: 0 });
  const resizeStartRef = useRef({ x: 0, startSize: 0 });

  const stopTimer = useCallback(() => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
  }, []);

  useEffect(() => {
    if (!isRunning) return;
    intervalRef.current = setInterval(() => setElapsed((p) => p + 1), 1000);
    return stopTimer;
  }, [isRunning, stopTimer]);

  const formatTime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  // Drag
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX, y: e.clientY, startX: timerX, startY: timerY };
  }, [timerX, timerY]);

  useEffect(() => {
    if (!isDragging) return;
    const move = (e: MouseEvent) => {
      setTimerX(dragStartRef.current.startX + e.clientX - dragStartRef.current.x);
      setTimerY(dragStartRef.current.startY + e.clientY - dragStartRef.current.y);
    };
    const up = () => setIsDragging(false);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, [isDragging]);

  // Resize
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    resizeStartRef.current = { x: e.clientX, startSize: fontSize };
  }, [fontSize]);

  useEffect(() => {
    if (!isResizing) return;
    const move = (e: MouseEvent) => {
      const d = e.clientX - resizeStartRef.current.x;
      setFontSize(Math.max(24, Math.min(140, resizeStartRef.current.startSize + d)));
    };
    const up = () => setIsResizing(false);
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, [isResizing]);

  const handleBgUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBgImage(URL.createObjectURL(file));
  };

  const handleNoiseUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setNoiseFile(file.name);
  };

  return (
    <div
      className="flex-1 flex flex-col min-w-0 relative overflow-hidden"
      style={bgImage ? { backgroundImage: `url(${bgImage})`, backgroundSize: "cover", backgroundPosition: "center" } : undefined}
    >
      {bgImage && <div className="absolute inset-0 bg-white/40" />}

      {/* Header */}
      <div className="relative flex items-center gap-2.5 px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0 z-20">
        <button onClick={onBack} className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">← 返回</button>
        <span className="text-black/20">|</span>
        <span className="text-lg leading-none">📖</span>
        <h2 className="text-sm font-semibold text-[#2c2c2c]">长门看书</h2>
      </div>

      <div className="relative flex-1 z-10">
        {/* ── Floating timer ── */}
        <div
          className="absolute select-none cursor-grab active:cursor-grabbing"
          style={{ left: timerX, top: timerY, fontSize, color: fontColor, lineHeight: 1 }}
          onMouseDown={handleDragStart}
        >
          <div className="tabular-nums font-light tracking-tight">
            {formatTime(elapsed)}
          </div>
          {/* Controls bar — visible on hover */}
          <div className="flex items-center gap-1.5 mt-1.5 opacity-0 hover:opacity-100 transition-opacity" style={{ fontSize: 13, color: fontColor }}>
            <button
              onClick={(e) => { e.stopPropagation(); setIsRunning(!isRunning); }}
              className="px-2 py-0.5 rounded hover:bg-black/5 hover:bg-opacity-20 transition text-xs"
              style={{ color: fontColor }}
            >
              {isRunning ? "暂停" : elapsed > 0 ? "继续" : "开始"}
            </button>
            {elapsed > 0 && !isRunning && (
              <button onClick={(e) => { e.stopPropagation(); stopTimer(); setElapsed(0); }} className="px-2 py-0.5 rounded hover:bg-black/5 transition text-xs">重置</button>
            )}
            <label className="relative px-2 py-0.5 rounded hover:bg-black/5 cursor-pointer text-xs">
              <input type="color" value={fontColor} onChange={(e) => setFontColor(e.target.value)} className="w-0 h-0 opacity-0 absolute" />
              颜色
            </label>
            <span onMouseDown={handleResizeStart} className="px-2 py-0.5 rounded hover:bg-black/5 text-xs cursor-se-resize">↕</span>
          </div>
        </div>

        {/* ── Settings — bottom right ── */}
        <div className="absolute bottom-4 right-4 flex flex-col items-end gap-1.5">
          <input ref={bgInputRef} type="file" accept="image/*" onChange={handleBgUpload} className="hidden" />
          <input ref={noiseInputRef} type="file" accept="audio/*" onChange={handleNoiseUpload} className="hidden" />

          <button onClick={() => bgInputRef.current?.click()}
            className="text-[11px] bg-white/60 backdrop-blur-sm hover:bg-white/80 px-2.5 py-1.5 rounded-lg border border-black/5 transition text-black/30 hover:text-blue-500">
            {bgImage ? "更换背景" : "背景"}
            {bgImage && <span onClick={(e) => { e.stopPropagation(); setBgImage(null); }} className="ml-1.5 text-black/20 hover:text-red-400">✕</span>}
          </button>

          <button onClick={() => noiseInputRef.current?.click()}
            className="text-[11px] bg-white/60 backdrop-blur-sm hover:bg-white/80 px-2.5 py-1.5 rounded-lg border border-black/5 transition text-black/30 hover:text-blue-500">
            {noiseFile ? noiseFile : "白噪音"}
            {noiseFile && <span onClick={(e) => { e.stopPropagation(); setNoiseFile(null); }} className="ml-1.5 text-black/20 hover:text-red-400">✕</span>}
          </button>

          {!bgImage && <div className="text-[10px] text-black/15">上传背景让氛围更沉浸</div>}
        </div>
      </div>
    </div>
  );
}
