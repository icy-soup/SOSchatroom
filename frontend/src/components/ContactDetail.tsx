import { useState, useEffect } from "react";
import { getCharacter } from "../characters";
import { fetchCharacterConfig, CharacterConfigDTO } from "../api";
import CharacterEditModal from "./CharacterEditModal";

interface ContactDetailProps {
  characterName: string;
  onStartChat: () => void;
}

export default function ContactDetail({ characterName, onStartChat }: ContactDetailProps) {
  const info = getCharacter(characterName);
  const [charConfig, setCharConfig] = useState<CharacterConfigDTO | null>(null);
  const [showEdit, setShowEdit] = useState(false);

  useEffect(() => {
    fetchCharacterConfig(characterName).then((data) => {
      setCharConfig(data.config || null);
    }).catch(() => {});
  }, [characterName]);

  const avatarDisplay = charConfig?.avatar || info.emoji;
  const displayName = charConfig?.display_name || info.name;
  const displayTitle = charConfig?.title || info.title;
  const signature = charConfig?.signature || info.description.split("\n")[0];
  const displayDescription = charConfig?.description || info.description.split("\n").slice(2).join("\n");

  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-white/30 px-8">
      {/* 角色头像 + 编辑按钮 */}
      <div className="relative mb-4">
        <div
          className="w-24 h-24 rounded-full flex items-center justify-center text-4xl shadow-lg overflow-hidden"
          style={{ background: `${info.color}20`, boxShadow: `0 4px 20px ${info.color}30` }}
        >
          {typeof avatarDisplay === "string" && avatarDisplay.startsWith("/uploads/") ? (
            <img src={avatarDisplay} alt={displayName} className="w-full h-full object-cover" />
          ) : (
            avatarDisplay
          )}
        </div>
        <button
          onClick={() => setShowEdit(true)}
          className="absolute -top-1 -right-1 w-7 h-7 bg-white rounded-full border border-black/10 flex items-center justify-center text-xs shadow-sm hover:bg-gray-50 transition"
          title="编辑角色"
        >
          ✏️
        </button>
      </div>

      {/* 名称 + 头衔 */}
      <h2 className="text-xl font-bold text-[#2c2c2c] mb-1">{displayName}</h2>
      <div className="text-sm font-medium" style={{ color: info.color }}>
        {displayTitle}
      </div>

      {/* 签名 */}
      <div
        className="mt-4 text-sm italic leading-relaxed text-center max-w-md px-4 py-3 rounded-xl"
        style={{
          background: `${info.color}08`,
          borderLeft: `3px solid ${info.color}40`,
          color: `${info.color}aa`,
        }}
      >
        {signature}
      </div>

      {/* 介绍 */}
      <div className="mt-4 text-sm text-black/60 leading-relaxed max-w-md whitespace-pre-wrap text-center">
        {displayDescription}
      </div>

      {/* 发起新对话 */}
      <button
        onClick={onStartChat}
        className="mt-6 px-6 py-2.5 rounded-xl text-sm font-semibold text-white shadow-md
                   hover:shadow-lg active:scale-[0.97] transition-all duration-150"
        style={{ background: `linear-gradient(135deg, ${info.color}, ${info.color}cc)` }}
      >
        发起新对话
      </button>

      {/* 编辑模态框 */}
      {showEdit && (
        <CharacterEditModal
          characterName={characterName}
          onClose={() => setShowEdit(false)}
          onSaved={() => {
            // Reload config after save
            fetchCharacterConfig(characterName).then((data) => {
              setCharConfig(data.config || null);
            }).catch(() => {});
          }}
        />
      )}
    </div>
  );
}
