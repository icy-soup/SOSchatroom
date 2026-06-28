/** 工具偏好管理 —— localStorage 持久化启用/禁用状态 */

const PREF_KEY = "tool_preferences";

interface ToolPrefs {
  [toolId: string]: boolean;
}

function getPrefs(): ToolPrefs {
  try {
    const raw = localStorage.getItem(PREF_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function savePrefs(prefs: ToolPrefs) {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
  } catch {
    /* quota exceeded */
  }
}

/** 检查工具是否启用（默认启用） */
export function isToolEnabled(toolId: string): boolean {
  const prefs = getPrefs();
  // 未设置过 = 默认启用
  return prefs[toolId] !== false;
}

/** 设置工具启用/禁用 */
export function setToolEnabled(toolId: string, enabled: boolean) {
  const prefs = getPrefs();
  prefs[toolId] = enabled;
  savePrefs(prefs);
}
