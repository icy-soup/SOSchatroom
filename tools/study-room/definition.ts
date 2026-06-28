import type { ToolDefinition } from '../../frontend/src/tools/types';
import StudyRoom from './StudyRoom';

const def: ToolDefinition = {
  id: "study_room",
  name: "长门看书",
  icon: "📖",
  kind: "control",
  description:
    "安静的空间有利于思考。\n" +
    "上传你的背景，开始计时。\n" +
    "有希会陪着你。",
  component: StudyRoom,
};

export default def;
