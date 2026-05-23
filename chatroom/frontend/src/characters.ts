import type { Character } from "./types";

export const CHARACTERS: Character[] = [
  { name: "凉宫春日", color: "#d97706", emoji: "🌟" },
  { name: "阿虚", color: "#2563eb", emoji: "🙄" },
  { name: "长门有希", color: "#7c3aed", emoji: "📖" },
  { name: "朝比奈实玖瑠", color: "#db2777", emoji: "🎀" },
  { name: "古泉一树", color: "#059669", emoji: "♟" },
];

export function getCharacter(name: string): Character {
  return CHARACTERS.find((c) => c.name === name) ?? {
    name,
    color: "#888",
    emoji: "❓",
  };
}
