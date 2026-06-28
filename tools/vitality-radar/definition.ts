import type { ToolDefinition } from '../../frontend/src/tools/types';

const def: ToolDefinition = {
  id: "vitality_radar",
  name: "春日生命力雷达",
  icon: "📡",
  kind: "llm",
  description:
    "喂！今天又在当行尸走肉了是吧？\n" +
    "说，能量耗哪儿了。然后给我去做一件事——现在！做完记下来！",
  placeholder:
    "说，今天发生了什么。\n或者我直接问你——哪刻你觉得自己像行尸走肉？",
};

export default def;
