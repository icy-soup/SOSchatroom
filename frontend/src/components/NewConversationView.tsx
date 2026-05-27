import { useState, useEffect } from "react";
import { CHARACTERS } from "../characters";
import SceneSettingsPanel from "./SceneSettingsPanel";

interface NewConversationViewProps {
  onStart: (partner: string, playerCharacter: string, sceneBackground?: string, absentCharacters?: string[]) => void;
  onCancel: () => void;
  presetPartner?: string | null;  // 从联系人页传入，跳过选对象步骤
}

export default function NewConversationView({ onStart, onCancel, presetPartner }: NewConversationViewProps) {
  const [step, setStep] = useState<"partner" | "player">(presetPartner ? "player" : "partner");
  const [partner, setPartner] = useState<string | null>(presetPartner ?? null);
  const [playerChar, setPlayerChar] = useState<string | null>(null);
  const [sceneBackground, setSceneBackground] = useState("");
  const [absentCharacters, setAbsentCharacters] = useState<string[]>([]);

  // 当 presetPartner 变化时同步
  useEffect(() => {
    if (presetPartner) {
      setPartner(presetPartner);
      setStep("player");
    }
  }, [presetPartner]);

  // 可选扮演角色 = 排除 partner
  const availablePlayers = CHARACTERS.filter((c) => c.name !== partner);

  // 群聊模式下，所有角色都可以选
  const isGroup = partner === "聊天室";

  return (
    <div className="flex-1 flex flex-col bg-white/30">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <button onClick={onCancel} className="text-xs text-black/40 hover:text-black/70 transition px-2 py-1 rounded hover:bg-black/5">← 返回</button>
        <span className="text-black/20">|</span>
        <span className="text-sm font-semibold text-[#2c2c2c]">新建对话</span>
      </div>

      <div className="flex-1 flex items-center justify-center px-8">
        <div className="max-w-lg w-full">
          {/* 步骤指示器（非预设时显示两步，预设时显示一步） */}
          {!presetPartner && (
            <div className="flex items-center justify-center gap-2 mb-8">
              <div className={`flex items-center gap-1.5 ${step === "partner" ? "text-purple-600" : "text-green-600"}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                  ${step === "partner" ? "bg-purple-100 text-purple-600" : "bg-green-100 text-green-600"}`}>
                  {step === "player" ? "✓" : "1"}
                </div>
                <span className="text-xs font-medium">选择聊天对象</span>
              </div>
              <div className="w-8 h-px bg-black/10" />
              <div className={`flex items-center gap-1.5 ${step === "player" ? "text-purple-600" : "text-black/30"}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
                  ${step === "player" ? "bg-purple-100 text-purple-600" : "bg-black/5 text-black/30"}`}>2</div>
                <span className="text-xs font-medium">选择扮演角色</span>
              </div>
            </div>
          )}

          {/* Step 1: 选择聊天对象 */}
          {step === "partner" && (
            <div>
              <h3 className="text-sm font-medium text-[#2c2c2c] mb-4 text-center">你想和谁聊天？</h3>
              <div className="grid grid-cols-2 gap-3">
                {CHARACTERS.map((c) => (
                  <button key={c.name} onClick={() => { setPartner(c.name); setStep("player"); }}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl border-2 border-transparent bg-white/80 hover:border-black/10 transition-all duration-150">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0"
                      style={{ background: `${c.color}18` }}>{c.emoji}</div>
                    <div className="text-left">
                      <div className="text-sm font-medium text-[#2c2c2c]">{c.name}</div>
                      <div className="text-[10px] text-black/40">{c.title}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: 选择扮演角色 */}
          {step === "player" && partner && (
            <div>
              <h3 className="text-sm font-medium text-[#2c2c2c] mb-4 text-center">
                {isGroup ? (
                  <>🏠 <strong>SOS团聊天室</strong> —— 你扮演谁？</>
                ) : (
                  <>{CHARACTERS.find(c => c.name === partner)?.emoji} 和 <strong>{partner}</strong> 聊天——你扮演谁？</>
                )}
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {(isGroup ? CHARACTERS : availablePlayers).map((c) => (
                  <button key={c.name} onClick={() => setPlayerChar(c.name)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all duration-150
                      ${playerChar === c.name ? "border-purple-300 bg-purple-50" : "border-transparent bg-white/80 hover:border-black/10"}`}>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0"
                      style={{ background: `${c.color}18` }}>{c.emoji}</div>
                    <div className="text-left">
                      <div className="text-sm font-medium text-[#2c2c2c]">{c.name}</div>
                      <div className="text-[10px] text-black/40">{c.title}</div>
                    </div>
                  </button>
                ))}
              </div>

              {/* Scene Settings */}
              <SceneSettingsPanel
                background={sceneBackground}
                absent={absentCharacters}
                allCharacters={CHARACTERS.map(c => c.name)}
                onBackgroundChange={setSceneBackground}
                onAbsentChange={setAbsentCharacters}
              />

              <div className="flex justify-center mt-6 gap-3">
                {!presetPartner && (
                  <button onClick={() => setStep("partner")}
                    className="text-xs text-black/40 hover:text-black/70 transition px-3 py-1.5 rounded-lg hover:bg-black/5">
                    ← 重新选聊天对象
                  </button>
                )}
                <button onClick={() => { if (partner && playerChar) onStart(partner, playerChar, sceneBackground, absentCharacters); }}
                  disabled={!playerChar}
                  className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-300 text-white px-6 py-2 rounded-lg text-sm font-medium transition">
                  开始对话
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
