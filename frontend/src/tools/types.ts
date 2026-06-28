import type { ComponentType } from "react";

/** 工具运行时类型：llm = 走 LLM 输入→结果，control = 自定义组件 */
export type ToolKind = "llm" | "control";

/** 工具定义——每个工具文件夹 index.ts 必须 export default 这个 */
export interface ToolDefinition {
  id: string;
  name: string;
  icon: string;
  kind: ToolKind;
  description: string;

  /** LLM 工具的输入框 placeholder */
  placeholder?: string;

  /** control 工具的自定义组件 */
  component?: ComponentType<{ onBack: () => void }>;
}
