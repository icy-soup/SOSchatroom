import type { ToolDefinition } from '../../frontend/src/tools/types';

const def: ToolDefinition = {
  id: "anti_inspiration",
  name: "阿虚反鸡汤净化器",
  icon: "🧹",
  kind: "llm",
  description:
    "……又来一句成功学？扔进来吧，我帮你拆了。\n" +
    "焦虑也能说——反正我也跑不掉。",
  placeholder:
    "把鸡汤扔进来，或者直接说你焦虑什么：\n" +
    "「努力就会成功」「总觉得落后别人一大截...」",
};

export default def;
