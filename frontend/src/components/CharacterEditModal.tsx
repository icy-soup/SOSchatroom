import { useState, useEffect, useRef } from "react";
import { fetchCharacterConfig, updateCharacterConfig, CharacterConfigDTO } from "../api";
import { getCharacter } from "../characters";

interface Props {
  characterName: string;
  onClose: () => void;
  onSaved: () => void;
}

const AVATAR_OPTIONS = ["🎭", "👤", "🌟", "🎪", "🎯", "💫", "✨", "🔥", "🌙", "⭐", "🎀", "🦋"];

export default function CharacterEditModal({ characterName, onClose, onSaved }: Props) {
  const charInfo = getCharacter(characterName);

  const [config, setConfig] = useState<CharacterConfigDTO>({
    character_name: characterName,
    display_name: "",
    avatar: "",
    signature: "",
    temperature: 0.7,
    reply_length: "normal",
    tone: "default",
    custom_instructions: "",
    title: "",
    description: "",
    api_url: "",
    model: "",
    api_key: "",
  });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchCharacterConfig(characterName).then((data) => {
      if (data.config) {
        setConfig(data.config);
      } else {
        // 无已保存配置时，用角色的默认值
        setConfig((prev) => ({
          ...prev,
          avatar: charInfo.emoji,
          signature: charInfo.description.split("\n")[0],
        }));
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [characterName]);

  const save = async () => {
    await updateCharacterConfig(characterName, config);
    onSaved();
    onClose();
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`/api/upload-avatar/${encodeURIComponent(characterName)}`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (data.url) setConfig((prev) => ({ ...prev, avatar: data.url }));
    } catch (e) {
      console.error("头像上传失败", e);
    }
    setUploading(false);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
        <div className="bg-white rounded-xl p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
          <p className="text-sm text-black/40">加载中...</p>
        </div>
      </div>
    );
  }

  const currentDisplay = config.display_name || charInfo.name;

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-xl w-[460px] max-h-[85vh] overflow-y-auto p-6 shadow-xl border border-black/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-base font-bold text-[#2c2c2c]">编辑角色 · {characterName}</h2>
          <button onClick={onClose} className="text-sm text-black/30 hover:text-black/60 transition">✕</button>
        </div>

        {/* Avatar */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1.5">头像</label>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center text-2xl border border-black/5 overflow-hidden">
              {config.avatar?.startsWith("/uploads/") ? (
                <img src={config.avatar} alt="头像" className="w-full h-full object-cover" />
              ) : (
                config.avatar || charInfo.emoji
              )}
            </div>
            <label className="px-3 py-1.5 text-xs bg-purple-600 text-white rounded-lg hover:bg-purple-500 cursor-pointer transition">
              {uploading ? "上传中..." : "上传图片"}
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarUpload} />
            </label>
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {AVATAR_OPTIONS.map((emoji) => (
              <button
                key={emoji}
                onClick={() => setConfig({ ...config, avatar: emoji })}
                className={`w-9 h-9 text-lg flex items-center justify-center rounded-lg border transition ${
                  config.avatar === emoji
                    ? "border-purple-400 bg-purple-50 ring-1 ring-purple-200"
                    : "border-black/10 hover:border-black/20 bg-white/60"
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>

        {/* Display Name */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">显示名称</label>
          <input
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none"
            placeholder={charInfo.name}
            value={config.display_name}
            onChange={(e) => setConfig({ ...config, display_name: e.target.value })}
          />
        </div>

        {/* Title */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">头衔</label>
          <input
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none"
            placeholder={charInfo.title}
            value={config.title}
            onChange={(e) => setConfig({ ...config, title: e.target.value })}
          />
        </div>

        {/* Signature */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">签名</label>
          <input
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none"
            placeholder={charInfo.description.split("\n")[0]}
            value={config.signature}
            onChange={(e) => setConfig({ ...config, signature: e.target.value })}
          />
        </div>

        {/* Description */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">角色介绍</label>
          <textarea
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm resize-none focus:border-purple-400 focus:outline-none placeholder-black/20"
            rows={3}
            placeholder={charInfo.description.split("\n").slice(2).join("\n")}
            value={config.description}
            onChange={(e) => setConfig({ ...config, description: e.target.value })}
          />
        </div>

        <hr className="border-black/5 mb-4" />

        {/* Temperature */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1.5">温度: {config.temperature.toFixed(1)}</label>
          <input
            type="range" min="0" max="2" step="0.1"
            value={config.temperature}
            onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
            className="w-full accent-purple-500"
          />
          <div className="flex justify-between text-[10px] text-black/20 mt-0.5">
            <span>精确</span>
            <span>创意</span>
          </div>
        </div>

        {/* Reply Length */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1.5">回复长度</label>
          <div className="flex gap-2">
            {(["short", "normal", "long"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setConfig({ ...config, reply_length: v })}
                className={`px-3 py-1.5 text-xs rounded-lg border transition ${
                  config.reply_length === v
                    ? "border-purple-400 bg-purple-50 text-purple-700"
                    : "border-black/10 text-black/50 hover:border-black/20"
                }`}
              >
                {v === "short" ? "简短" : v === "normal" ? "适中" : "详细"}
              </button>
            ))}
          </div>
        </div>

        {/* Tone */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1.5">语气</label>
          <div className="flex gap-2">
            {(["default", "lively", "calm"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setConfig({ ...config, tone: v })}
                className={`px-3 py-1.5 text-xs rounded-lg border transition ${
                  config.tone === v
                    ? "border-purple-400 bg-purple-50 text-purple-700"
                    : "border-black/10 text-black/50 hover:border-black/20"
                }`}
              >
                {v === "default" ? "保持默认" : v === "lively" ? "更活泼" : "更冷静"}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Instructions */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1.5">自定义指令</label>
          <textarea
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm resize-none focus:border-purple-400 focus:outline-none placeholder-black/20"
            rows={3}
            placeholder="追加到角色 prompt 末尾的额外指令……"
            value={config.custom_instructions}
            onChange={(e) => setConfig({ ...config, custom_instructions: e.target.value })}
          />
        </div>

        <hr className="border-black/5 mb-4" />

        {/* API URL */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">API 地址（留空=全局）</label>
          <input
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none"
            placeholder="https://api.deepseek.com"
            value={config.api_url}
            onChange={(e) => setConfig({ ...config, api_url: e.target.value })}
          />
        </div>

        {/* Model */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">模型（留空=全局）</label>
          <input
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none"
            placeholder="deepseek-v4-flash"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
          />
        </div>

        {/* API Key */}
        <div className="mb-4">
          <label className="text-[11px] text-black/40 font-medium block mb-1">API Key（留空=使用全局 Key）</label>
          <input
            type="password"
            className="w-full border border-black/10 rounded-lg px-3 py-2 text-sm focus:border-purple-400 focus:outline-none"
            placeholder="sk-..."
            value={config.api_key || ''}
            onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
          />
        </div>

        <div className="flex gap-2 justify-end pt-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-black/40 hover:text-black/70 transition">取消</button>
          <button onClick={save} className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition">保存</button>
        </div>
      </div>
    </div>
  );
}
