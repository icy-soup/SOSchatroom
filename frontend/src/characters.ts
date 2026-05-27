import type { Character } from "./types";

export const CHARACTERS: (Character & { title: string; description: string })[] = [
  {
    name: "凉宫春日",
    color: "#d97706",
    emoji: "🌟",
    title: "SOS团团长",
    description:
      "「我对普通的人类没有兴趣。你们之中要是有外星人、未来人、异世界的人、超能力者。就尽管来找我吧！」\n\n坚信世界不可能是表面看到的那样简单。行动力爆表，说干就干。SOS团的创始人和绝对领袖。虽然嘴上不饶人，但其实比谁都重视团员。",
  },
  {
    name: "阿虚",
    color: "#2563eb",
    emoji: "🙄",
    title: "吐槽担当",
    description:
      "「为什么我非得……唉，算了。」\n\nSOS团唯一的正常（自称）人。总是抱怨但每次都会去做。在团长暴走时唯一能拉住她的人。嘴上说麻烦，实际上比谁都可靠。",
  },
  {
    name: "长门有希",
    color: "#7c3aed",
    emoji: "📖",
    title: "沉默的资讯统合体",
    description:
      "……（看书）\n\n文艺部教室的沉默读书人。真实身份是资讯统合思念体制造的对人用联系装置（外星人）。话极少但信息量极大。拥有改变世界的能力，却选择坐在角落看书。",
  },
  {
    name: "朝比奈实玖瑠",
    color: "#db2777",
    emoji: "🎀",
    title: "SOS团吉祥物",
    description:
      "「那、那个……对不起……」\n\n未来人。从比现代更远的未来来到这个时代执行任务。被春日强行拉入SOS团担任吉祥物+强制换装担当。性格胆小温柔但关键时刻很坚强。",
  },
  {
    name: "古泉一树",
    color: "#059669",
    emoji: "♟",
    title: "微笑的超能力者",
    description:
      "「——呵呵，这可有趣了。」\n\n表面上是转学到县立北高的二年级生，实际上是被「机关」派来观察春日的超能力者。永远带着微笑说着意味深长的话。自称是「春日力量的观测者」。",
  },
];

export function getCharacter(name: string) {
  return CHARACTERS.find((c) => c.name === name) ?? {
    name,
    color: "#888",
    emoji: "❓",
    title: "",
    description: "",
  };
}
