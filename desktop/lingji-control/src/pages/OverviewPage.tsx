import { useCallback, useMemo } from "react";
import { Empty, Notice } from "../components/ui";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import { OwnerMemoryCardsApi } from "./ownerMemoryCardsApi";
import { ownerFacingConclusion, type OwnerMemoryCard } from "./ownerMemoryCardsTypes";
import { pendingActionsFrom, type PendingAction, type PendingActionsResponse } from "../contracts/workFact";
import { usePollingResource } from "../hooks/usePollingResource";

const formatTime = (value: unknown): string => {
  if (!value) return "";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
};

/**
 * 首页 = 产品叙事，不是监控面板（主人 2026-09-28 反馈重做）。
 * 三段式：①灵机今天为你记住了什么（关键节点，大字卡片）
 *        ②系统自动处理中的事项（失败治理生成的记录，只读可见，主人 2026-09-29
 *          指示：不再留"等主人拍板"的环节，问题自动亮在状态页）
 *        ③底部一行系统状态。
 * 数据全部来自既有只读投影（owner memory cards / pending actions），
 * 不新增第二套存储。
 */
export default function OverviewPage({ api, active, onNavigate }: { data: Row | null; api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const cardsApi = useMemo(() => new OwnerMemoryCardsApi(api), [api]);
  const cardsResource = usePollingResource({
    fetcher: useCallback((signal: AbortSignal) => cardsApi.list(0, signal, 8, "current"), [cardsApi]),
    enabled: active,
    intervalMs: 20_000,
    staleAfterMs: 45_000,
    pauseWhenHidden: true,
  });
  const pendingResource = usePollingResource({
    fetcher: useCallback((signal: AbortSignal) => api.get<PendingActionsResponse>("/api/work/pending-actions", { signal }), [api]),
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 25_000,
    pauseWhenHidden: true,
  });

  const cards: OwnerMemoryCard[] = cardsResource.data?.items ?? [];
  const remembered = cards.filter((card) => {
    const conclusion = ownerFacingConclusion(card);
    return Boolean(conclusion?.text || card.conclusion || (card.developments?.length ?? 0) > 0);
  });
  const pending: PendingAction[] | null = pendingActionsFrom(pendingResource.data);
  const ownerPending = (pending ?? []).filter((item) => !item.resolved && item.actor === "owner");
  const systemPending = (pending ?? []).filter((item) => !item.resolved && item.actor !== "owner");

  const summarize = (card: OwnerMemoryCard): { title: string; body: string } => {
    const conclusion = ownerFacingConclusion(card);
    const title = card.topic || "";
    const body = conclusion?.text || card.conclusion || (card.developments?.[card.developments.length - 1] ?? "");
    return { title, body };
  };

  // 断连时诚实呈现：数据没有丢失，恢复后自动刷新——不能把"没数据"说成
  // "正常现象，没有内容"（2026-09-29 主人报"UI 什么都不显示"的直接观感来源）。
  if (!active) {
    return (
      <div className="home-narrative">
        <section className="home-section">
          <h2 className="home-headline">灵机为你记住了什么</h2>
          <Notice kind="warning">与灵机的连接暂时断开，正在自动恢复。数据没有丢失，恢复后这里会自动刷新。</Notice>
        </section>
        <section className="home-section home-footer">
          <span className="home-footer-line">灵机在本机自动整理你的记录：只记关键节点，原文永远保留，随时可回溯。</span>
        </section>
      </div>
    );
  }

  return (
    <div className="home-narrative">
      <section className="home-section">
        <h2 className="home-headline">灵机为你记住了什么</h2>
        {cardsResource.loading && cards.length === 0 ? (
          <p className="home-muted">正在读取记忆…</p>
        ) : cardsResource.error ? (
          <Notice kind="warning">记忆卡片暂时读取失败，正在自动重试；已记内容不会丢失。</Notice>
        ) : remembered.length === 0 ? (
          <Empty text="最近没有值得记住的关键内容——正常现象，灵机只记关键节点，不为记忆而记忆。" />
        ) : (
          <>
            <p className="home-summary">
              最近为你提炼了 <strong>{remembered.length}</strong> 条关键记忆，点开可看原文出处。
            </p>
            <div className="home-cards">
              {remembered.slice(0, 6).map((card) => {
                const { title, body } = summarize(card);
                return (
                  <button key={card.memory_id} className="home-memory-card" onClick={() => onNavigate("memory_library")}>
                    <strong className="home-memory-title">{title}</strong>
                    <span className="home-memory-body">{body || "（见记忆库详情）"}</span>
                    <span className="home-memory-meta">{formatTime(card.as_of || card.source?.latest_evidence_at)}</span>
                  </button>
                );
              })}
            </div>
          </>
        )}
        <button className="home-secondary-link" onClick={() => onNavigate("memory_library")}>
          去记忆库看全部 →
        </button>
      </section>

      <section className="home-section">
        <h2 className="home-headline">系统自动处理中的事项</h2>
        {pending === null ? (
          <p className="home-muted">正在读取状态…</p>
        ) : ownerPending.length === 0 ? (
          <Empty text="一切正常——没有需要留意的异常。" />
        ) : (
          <>
            <p className="home-summary">
              <strong>{ownerPending.length}</strong> 条事项由灵机自动重试或保守处理，无需你操作：
            </p>
            <div className="home-actions">
              {ownerPending.map((item) => (
                <div key={item.action_id} className="home-action-card owner">
                  <span className="home-action-body">{item.description}</span>
                  <span className="home-action-meta">{formatTime(item.created_at)}</span>
                </div>
              ))}
            </div>
            <button className="home-secondary-link" onClick={() => onNavigate("attention")}>
              看全部状态 →
            </button>
          </>
        )}
        {systemPending.length > 0 && (
          <p className="home-muted">另有 {systemPending.length} 条系统内部记录，无需你处理。</p>
        )}
      </section>

      <section className="home-section home-footer">
        <span className="home-footer-line">
          灵机在本机自动整理你的记录：只记关键节点，原文永远保留，随时可回溯。
        </span>
      </section>

      {cardsResource.stale && (
        <Notice kind="warning">与核心的连接不稳定，以上内容可能滞后。</Notice>
      )}
    </div>
  );
}
