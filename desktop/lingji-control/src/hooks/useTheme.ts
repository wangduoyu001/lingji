import { useCallback, useEffect, useState } from "react";

export type ThemeId = "nord" | "aurora" | "cyber" | "command";

export const THEMES: Array<{ id: ThemeId; label: string; dot: string }> = [
  { id: "nord", label: "Codex 深蓝灰", dot: "#88c0d0" },
  { id: "aurora", label: "极光青绿", dot: "#77d6b3" },
  { id: "cyber", label: "赛博紫罗兰", dot: "#a78bfa" },
  { id: "command", label: "指挥舱琥珀", dot: "#38bdf8" },
];

const STORAGE_KEY = "lingji-theme";
const DEFAULT_THEME: ThemeId = "nord";

function readStoredTheme(): ThemeId {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return THEMES.some((t) => t.id === raw) ? (raw as ThemeId) : DEFAULT_THEME;
  } catch {
    return DEFAULT_THEME;
  }
}

/** 四主题切换（2026-09-30 主人拍板"都要"）：data-theme 挂根容器 + localStorage 持久化。 */
export function useTheme() {
  const [theme, setThemeState] = useState<ThemeId>(() => readStoredTheme());

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // localStorage 不可用时主题仍然生效（仅不持久化）。
    }
  }, []);

  return { theme, setTheme };
}
