import { useState, useEffect } from "react";
import { CHARACTERS } from "../characters";

interface PerCharacterEntry {
  api_url: string;
  model: string;
}

type CharacterConfig = Record<string, PerCharacterEntry>;

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: {
    apiKey: string;
    apiUrl: string;
    model: string;
    characterConfig: CharacterConfig;
  }) => void;
  hasApiKey: boolean;
  initialApiUrl: string;
  initialModel: string;
}

function emptyCharacterConfig(): CharacterConfig {
  const cfg: CharacterConfig = {};
  for (const c of CHARACTERS) {
    cfg[c.name] = { api_url: "", model: "" };
  }
  return cfg;
}

export default function SettingsModal({
  open,
  onClose,
  onSave,
  hasApiKey,
  initialApiUrl,
  initialModel,
}: SettingsModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [apiUrl, setApiUrl] = useState(initialApiUrl);
  const [model, setModel] = useState(initialModel);
  const [charConfig, setCharConfig] = useState<CharacterConfig>(emptyCharacterConfig);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (open) {
      setApiUrl(initialApiUrl);
      setModel(initialModel);
      setApiKey("");
      setCharConfig(emptyCharacterConfig());
      setShowAdvanced(false);
    }
  }, [open, initialApiUrl, initialModel]);

  if (!open) return null;

  const updateChar = (name: string, field: "api_url" | "model", value: string) => {
    setCharConfig((prev) => ({
      ...prev,
      [name]: { ...prev[name], [field]: value },
    }));
  };

  const handleSave = () => {
    // Strip empty entries
    const cleaned: CharacterConfig = {};
    for (const c of CHARACTERS) {
      const entry = charConfig[c.name];
      if (entry?.api_url || entry?.model) {
        cleaned[c.name] = {
          api_url: entry.api_url || "",
          model: entry.model || "",
        };
      }
    }
    onSave({ apiKey, apiUrl, model, characterConfig: cleaned });
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="bg-[#faf7f2] rounded-2xl p-6 w-[520px] max-w-[94vw] shadow-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#2c2c2c]">设置</h2>
          <button
            onClick={onClose}
            className="text-black/30 hover:text-black/60 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        {/* ── 全局设置 ── */}
        <div className="space-y-3">
          <div>
            <label className="text-xs text-black/40 block mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                hasApiKey
                  ? "已配置（留空则保持当前值）"
                  : "sk-..."
              }
              className="w-full bg-white border border-black/10 rounded-lg px-3 py-2 text-sm
                         focus:border-purple-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs text-black/40 block mb-1">API 地址</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              placeholder="https://api.deepseek.com"
              className="w-full bg-white border border-black/10 rounded-lg px-3 py-2 text-sm
                         focus:border-purple-400 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-xs text-black/40 block mb-1">模型</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="deepseek-v4-flash"
              className="w-full bg-white border border-black/10 rounded-lg px-3 py-2 text-sm
                         focus:border-purple-400 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                hasApiKey ? "bg-green-500" : "bg-black/20"
              }`}
            />
            <span className={hasApiKey ? "text-green-600" : "text-black/30"}>
              {hasApiKey ? "已配置" : "未设置"}
            </span>
          </div>
        </div>

        {/* ── 角色独立配置 ── */}
        <div className="mt-4 pt-4 border-t border-black/5">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center justify-between w-full text-left text-sm font-medium text-black/50 hover:text-black/70 transition"
          >
            <span>角色独立 API 配置（可选）</span>
            <span className="text-xs">{showAdvanced ? "收起" : "展开"}</span>
          </button>

          {showAdvanced && (
            <div className="mt-3 space-y-4">
              {CHARACTERS.map((c) => (
                <div
                  key={c.name}
                  className="bg-white/60 rounded-xl p-3 border border-black/5"
                >
                  <div className="flex items-center gap-1.5 mb-2">
                    <span>{c.emoji}</span>
                    <span className="text-sm font-medium" style={{ color: c.color }}>
                      {c.name}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-black/30 block mb-0.5">
                        API 地址
                      </label>
                      <input
                        type="text"
                        value={charConfig[c.name]?.api_url ?? ""}
                        onChange={(e) => updateChar(c.name, "api_url", e.target.value)}
                        placeholder="留空=全局"
                        className="w-full bg-white border border-black/10 rounded-lg px-2.5 py-1.5 text-xs
                                   focus:border-purple-400 focus:outline-none placeholder-black/15"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-black/30 block mb-0.5">
                        Model
                      </label>
                      <input
                        type="text"
                        value={charConfig[c.name]?.model ?? ""}
                        onChange={(e) => updateChar(c.name, "model", e.target.value)}
                        placeholder="留空=全局"
                        className="w-full bg-white border border-black/10 rounded-lg px-2.5 py-1.5 text-xs
                                   focus:border-purple-400 focus:outline-none placeholder-black/15"
                      />
                    </div>
                  </div>
                </div>
              ))}
              <p className="text-[10px] text-black/20 leading-relaxed">
                每个角色可独立配置 API 地址和模型。留空则使用全局设置。
              </p>
            </div>
          )}
        </div>

        {/* ── 聊天背景 ── */}
        <div className="mt-4 pt-4 border-t border-black/5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-black/50">聊天背景</span>
            <button
              onClick={() => {
                document.body.style.backgroundImage = "";
                document.body.style.backgroundSize = "";
                document.body.style.backgroundPosition = "";
                document.body.style.backgroundAttachment = "";
              }}
              className="text-[10px] text-black/30 hover:text-red-500 transition"
            >
              移除背景
            </button>
          </div>
          <label className="flex items-center gap-2 cursor-pointer bg-white/60 border border-black/10 rounded-lg px-3 py-2 hover:border-purple-300 transition">
            <span className="text-xs text-black/40">选择图片</span>
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                try {
                  const formData = new FormData();
                  formData.append("file", file);
                  const res = await fetch("/api/upload-background", {
                    method: "POST",
                    body: formData,
                  });
                  const data = await res.json();
                  if (data.url) {
                    document.body.style.backgroundImage = `url(${data.url})`;
                    document.body.style.backgroundSize = "cover";
                    document.body.style.backgroundPosition = "center";
                    document.body.style.backgroundAttachment = "fixed";
                  }
                } catch {
                  alert("背景上传失败，请检查服务器连接");
                }
              }}
            />
          </label>
          <p className="text-[10px] text-black/20 mt-1">
            图片上传到服务器，重启后不丢失
          </p>
        </div>

        <div className="flex justify-end pt-4">
          <button
            onClick={handleSave}
            className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
          >
            保存
          </button>
        </div>

        <div className="mt-3 pt-3 border-t border-black/5">
          <p className="text-[10px] text-black/20 leading-relaxed">
            API Key 仅保存在当前浏览器会话中，不会存到磁盘。
          </p>
        </div>
      </div>
    </div>
  );
}
