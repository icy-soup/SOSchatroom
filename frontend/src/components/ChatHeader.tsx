import { getCharacter } from "../characters";

interface ChatHeaderProps {
  characterName: string | null;
  messageCount: number;
  onClear: () => void;
  onSceneSettings?: () => void;
}

export default function ChatHeader({ characterName, messageCount, onClear, onSceneSettings }: ChatHeaderProps) {
  const isGroup = characterName === "聊天室" || characterName === "group";

  // 无角色时显示通用标题
  if (!characterName) {
    return (
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-[#2c2c2c]">SOS团聊天室</h2>
        </div>
      </div>
    );
  }

  // 群聊
  if (isGroup) {
    return (
      <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-base shrink-0 bg-gradient-to-br from-purple-100 to-pink-100">
            🏠
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[#2c2c2c]">SOS团聊天室</h2>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {onSceneSettings && (
            <button onClick={onSceneSettings} className="text-[11px] text-black/30 hover:text-black/60 transition px-2 py-1 rounded hover:bg-black/5" title="场景设置">🎬</button>
          )}
          <button onClick={onClear} className="text-[11px] text-black/30 hover:text-black/60 transition px-2 py-1 rounded hover:bg-black/5" title="清除对话">清除</button>
        </div>
      </div>
    );
  }

  const info = getCharacter(characterName);

  return (
    <div className="flex items-center justify-between px-5 py-3 border-b border-black/5 bg-white/60 backdrop-blur-sm shrink-0">
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-base shrink-0"
          style={{ background: `${info.color}18` }}
        >
          {info.emoji}
        </div>
        <div>
          <h2 className="text-sm font-semibold text-[#2c2c2c]">{characterName}</h2>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {onSceneSettings && (
          <button onClick={onSceneSettings} className="text-[11px] text-black/30 hover:text-black/60 transition px-2 py-1 rounded hover:bg-black/5" title="场景设置">🎬</button>
        )}
        <button
          onClick={onClear}
          className="text-[11px] text-black/30 hover:text-black/60 transition px-2 py-1 rounded
                     hover:bg-black/5"
          title="清除对话"
        >
          清除
        </button>
      </div>
    </div>
  );
}
