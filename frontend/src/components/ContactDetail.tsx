import { getCharacter } from "../characters";

interface ContactDetailProps {
  characterName: string;
  onStartChat: () => void;
}

export default function ContactDetail({ characterName, onStartChat }: ContactDetailProps) {
  const info = getCharacter(characterName);

  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-white/30 px-8">
      {/* 角色头像 */}
      <div
        className="w-24 h-24 rounded-full flex items-center justify-center text-4xl mb-4 shadow-lg"
        style={{ background: `${info.color}20`, boxShadow: `0 4px 20px ${info.color}30` }}
      >
        {info.emoji}
      </div>

      {/* 名称 + 头衔 */}
      <h2 className="text-xl font-bold text-[#2c2c2c] mb-1">{info.name}</h2>
      <div className="text-sm font-medium" style={{ color: info.color }}>
        {info.title}
      </div>

      {/* 签名/引用 */}
      <div
        className="mt-4 text-sm italic leading-relaxed text-center max-w-md px-4 py-3 rounded-xl"
        style={{
          background: `${info.color}08`,
          borderLeft: `3px solid ${info.color}40`,
          color: `${info.color}aa`,
        }}
      >
        {info.description.split("\n")[0]}
      </div>

      {/* 介绍 */}
      <div className="mt-4 text-sm text-black/60 leading-relaxed max-w-md whitespace-pre-wrap text-center">
        {info.description.split("\n").slice(2).join("\n")}
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
    </div>
  );
}
