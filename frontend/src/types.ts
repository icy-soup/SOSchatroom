export type PanelView = "chat" | "contacts" | "tools" | "history";

export interface Character {
  name: string;
  color: string;
  emoji: string;
}

export interface Message {
  character: string;
  text: string;
  isBot: boolean;
  id: string;
}

export interface ChatConfig {
  demoMode: boolean;
  hasApiKey: boolean;
  apiUrl: string;
  model: string;
}

export interface Conversation {
  id: string;
  partner: string;          // AI角色（跟谁聊）
  playerCharacter: string;  // 玩家扮演的角色（我是谁）
  title: string;            // 默认 "{partner} · 扮演{player}", 可重命名
  messages: Message[];
  createdAt: number;
}

export type WsMessage =
  | { type: "config"; demo_mode: boolean; has_api_key: boolean; api_url: string; model: string }
  | { type: "config_updated"; has_api_key: boolean; demo_mode: boolean; api_url: string; model: string }
  | { type: "character_ready"; character: string }
  | { type: "message"; character: string; text: string; is_bot: boolean }
  | { type: "style_transferred"; original: string; transformed: string }
  | { type: "system"; text: string }
  | { type: "error"; text: string }
  | { type: "api_key_status"; has_api_key: boolean; demo_mode: boolean }
  | { type: "thinking"; character: string }
  | { type: "thinking_clear"; character: string }
  | { type: "tool_result"; tool_id: string; result: string }
  | { type: "stylized"; original: string; transformed: string | null; already_in_character: boolean; message: string; score?: number };
