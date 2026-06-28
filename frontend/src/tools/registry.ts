import type { ToolDefinition } from "./types";

/** 自动扫描根目录 tools/<id>/definition.ts，零注册。
 *  新建工具只需在 tools/<id>/ 下按规范写 definition.ts，重启即用。 */
const modules = import.meta.glob("../../../tools/*/definition.ts", { eager: true });

export const ALL_TOOLS: ToolDefinition[] = Object.values(modules)
  .map((m) => (m as any).default)
  .filter(Boolean);

export function getTool(id: string): ToolDefinition | undefined {
  return ALL_TOOLS.find((t) => t.id === id);
}
