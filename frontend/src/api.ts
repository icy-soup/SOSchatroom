const BASE = "/api";

async function fetchJSON(url: string, options?: RequestInit) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return res.json();
}

export interface ConversationDTO {
  id: string;
  character: string;
  type: "single" | "group";
  title: string;
  scene_background: string;
  absent_characters: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  preview: string;
  player_character: string;
}

export interface MessageDTO {
  id: number;
  conversation_id: string;
  role: string;
  content: string;
  is_bot: number;
  created_at: string;
}

export interface CharacterConfigDTO {
  character_name: string;
  display_name: string;
  avatar: string;
  signature: string;
  temperature: number;
  reply_length: string;
  tone: string;
  custom_instructions: string;
  title: string;
  description: string;
  api_url: string;
  model: string;
  api_key: string;
}

export async function fetchConversations(): Promise<{ conversations: ConversationDTO[] }> {
  return fetchJSON(`${BASE}/conversations`);
}

export async function createConversation(data: {
  character: string;
  type: string;
  title?: string;
  scene_background?: string;
  absent_characters?: string[];
  id?: string;
  player_character?: string;
}): Promise<{ id: string }> {
  return fetchJSON(`${BASE}/conversations`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchConversationDetail(id: string): Promise<{
  conversation: ConversationDTO;
  messages: MessageDTO[];
}> {
  return fetchJSON(`${BASE}/conversations/${encodeURIComponent(id)}`);
}

export async function deleteConversation(id: string): Promise<void> {
  await fetchJSON(`${BASE}/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function updateScene(
  id: string,
  data: { scene_background?: string; absent_characters?: string[] }
): Promise<void> {
  await fetchJSON(`${BASE}/conversations/${encodeURIComponent(id)}/scene`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function batchImportConversations(data: {
  conversations: any[];
  messages: Record<string, any[]>;
}): Promise<void> {
  await fetchJSON(`${BASE}/conversations/batch-import`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchCharacterConfigs(): Promise<{ configs: CharacterConfigDTO[] }> {
  return fetchJSON(`${BASE}/character-configs`);
}

export async function fetchCharacterConfig(name: string): Promise<{ config: CharacterConfigDTO | null }> {
  return fetchJSON(`${BASE}/character-configs/${encodeURIComponent(name)}`);
}

export async function updateCharacterConfig(name: string, data: Partial<CharacterConfigDTO>): Promise<void> {
  await fetchJSON(`${BASE}/character-configs/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}
