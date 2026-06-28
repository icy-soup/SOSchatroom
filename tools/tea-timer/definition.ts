import type { ToolDefinition } from '../../frontend/src/tools/types';
import TeaTimer from './TeaTimer';

const def: ToolDefinition = {
  id: "tea_timer",
  name: "朝比奈喝茶工具",
  icon: "🍵",
  kind: "control",
  description:
    "那、那个……到时间了哦。\n" +
    "茶已经泡好了，休息一下吧……\n" +
    "我会提醒您的，绝对不会让您忘记的。",
  component: TeaTimer,
};

export default def;
