import { useState, useRef, useEffect, useCallback } from "react";

type TimerState = "idle" | "running" | "done";

const PRESETS = [
  { label: "30 分", seconds: 30 * 60 },
  { label: "60 分", seconds: 60 * 60 },
  { label: "90 分", seconds: 90 * 60 },
];

export default function TeaTimer({ onBack }: { onBack: () => void }) {
  const [timerState, setTimerState] = useState<TimerState>("idle");
  const [remaining, setRemaining] = useState(0);
  const [customMin, setCustomMin] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stopTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startTimer = useCallback((seconds: number) => {
    stopTimer();
    setRemaining(seconds);
    setTimerState("running");
  }, [stopTimer]);

  useEffect(() => {
    if (timerState !== "running") return;
    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          stopTimer();
          setTimerState("done");
          if (audioRef.current) {
            audioRef.current.currentTime = 0;
            audioRef.current.play().catch(() => {});
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return stopTimer;
  }, [timerState, stopTimer]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  const handleCustomSubmit = () => {
    const mins = parseInt(customMin, 10);
    if (isNaN(mins) || mins < 1 || mins > 180) return;
    startTimer(mins * 60);
    setCustomMin("");
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-white/30">
      <div className="flex items-center gap-2.5 px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <button
          onClick={onBack}
          className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5"
        >
          ← 返回
        </button>
        <span className="text-black/20">|</span>
        <span className="text-lg leading-none">🍵</span>
        <h2 className="text-sm font-semibold text-[#2c2c2c]">朝比奈喝茶工具</h2>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-8 relative">
        {/* ── done 状态：全屏大字 ── */}
        {timerState === "done" ? (
          <div className="flex flex-col items-center gap-6 animate-[fadeIn_0.5s_ease]">
            <div className="text-8xl">💧</div>
            <div className="text-5xl font-bold text-pink-500">喝水了！</div>
            <p className="text-lg text-pink-400/70 text-center leading-relaxed">
              那、那个……茶泡好了哦。<br />
              休息一下吧，一直坐着对身体不好的……
            </p>
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => { setTimerState("idle"); setRemaining(0); }}
                className="px-6 py-2.5 bg-pink-500 hover:bg-pink-400 text-white
                           rounded-xl font-medium transition shadow-sm"
              >
                再来一次
              </button>
              <button
                onClick={onBack}
                className="px-6 py-2.5 bg-black/5 hover:bg-black/10 text-black/40
                           rounded-xl transition"
              >
                返回
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* 动画占位（非 done 时显示） */}
            <div
              id="tea-pour-animation"
              className="w-28 h-28 rounded-full bg-pink-100/60 border border-pink-200/50
                         flex items-center justify-center text-4xl mb-8"
            >
              🍵
            </div>

            {/* 音效占位 */}
            <audio ref={audioRef} id="tea-sound" preload="none" />

            {/* 倒计时 */}
            {timerState === "running" && (
              <div className="text-6xl font-light text-[#2c2c2c] tabular-nums mb-6">
                {formatTime(remaining)}
              </div>
            )}

            {/* idle 控件 */}
            {timerState === "idle" && (
              <div className="flex flex-col items-center gap-6">
                <div className="flex gap-4">
                  {PRESETS.map((p) => (
                    <button
                      key={p.seconds}
                      onClick={() => startTimer(p.seconds)}
                      className="px-6 py-3 bg-pink-500 hover:bg-pink-400 text-white text-base
                                 rounded-xl font-medium transition shadow-sm"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-3 text-sm text-black/40">
                  <span>自定义：</span>
                  <input
                    type="number"
                    min={1}
                    max={180}
                    value={customMin}
                    onChange={(e) => setCustomMin(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleCustomSubmit()}
                    placeholder="分钟"
                    className="w-20 px-3 py-2 bg-white border border-black/10 rounded-xl
                               text-sm text-[#2c2c2c] focus:border-pink-400 focus:outline-none text-center"
                  />
                  <span>分钟</span>
                  <button
                    onClick={handleCustomSubmit}
                    disabled={!customMin}
                    className="px-4 py-2 bg-pink-500 hover:bg-pink-400 disabled:bg-pink-300
                               text-white text-sm rounded-xl font-medium transition"
                  >
                    开始
                  </button>
                </div>
              </div>
            )}

            {/* running 控件 */}
            {timerState === "running" && (
              <button
                onClick={() => { stopTimer(); setTimerState("idle"); setRemaining(0); }}
                className="px-5 py-2.5 bg-black/5 hover:bg-black/10 text-black/40
                           rounded-xl transition text-sm"
              >
                取消定时
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
