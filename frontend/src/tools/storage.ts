/** 工具历史记录 —— localStorage 持久化 */

export interface ToolHistoryEntry {
  id: string;
  toolId: string;
  input: string;
  output: string;
  timestamp: number;
}

function storageKey(toolId: string) {
  return `tool_history:${toolId}`;
}

/** 获取某个工具的所有历史记录（按时间倒序） */
export function getToolHistory(toolId: string): ToolHistoryEntry[] {
  try {
    const raw = localStorage.getItem(storageKey(toolId));
    if (!raw) return [];
    const entries: ToolHistoryEntry[] = JSON.parse(raw);
    return entries.sort((a, b) => b.timestamp - a.timestamp);
  } catch {
    return [];
  }
}

/** 保存一条工具调用记录 */
export function saveToolHistory(toolId: string, input: string, output: string): void {
  try {
    const entries = getToolHistory(toolId);
    entries.unshift({
      id: `${toolId}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      toolId,
      input,
      output,
      timestamp: Date.now(),
    });
    // 最多保留 50 条
    localStorage.setItem(storageKey(toolId), JSON.stringify(entries.slice(0, 50)));
  } catch {
    // localStorage 满则静默丢弃
  }
}

/** 删除单条历史记录 */
export function deleteToolHistoryEntry(toolId: string, entryId: string): void {
  try {
    const entries = getToolHistory(toolId);
    const filtered = entries.filter((e) => e.id !== entryId);
    localStorage.setItem(storageKey(toolId), JSON.stringify(filtered));
  } catch {
    // 静默丢弃
  }
}

/** 清空某个工具的历史 */
export function clearToolHistory(toolId: string): void {
  localStorage.removeItem(storageKey(toolId));
}
