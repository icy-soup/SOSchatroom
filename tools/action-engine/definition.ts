import type { ToolDefinition } from '../../frontend/src/tools/types';
import ActionEngine from './ActionEngine';

const def: ToolDefinition = {
  id: "action_engine",
  name: "春日行动引擎",
  icon: "⚡",
  kind: "control",
  description:
    "喂！清单丢过来！三秒排完——哪个先做哪个扔，我说了算！\n" +
    "打完勾记得来汇报！本团长会盯着你的！",
  placeholder:
    "把待办和期限丢过来：\n1. 写周报（明天截止）\n2. 健身（拖一个月了）\n3. ...",
  component: ActionEngine,
};

export default def;
