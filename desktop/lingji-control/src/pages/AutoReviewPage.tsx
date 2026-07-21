import { useCallback, useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import { Empty, Metric, Notice, Panel } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageProps, Row } from "../types";
import type {
  AutoReviewAudit,
  AutoReviewDecisionPage,
  AutoReviewMetrics,
  AutoReviewStatus,
} from "./autoReviewTypes";

const actionLabel = (value: string) => ({
  would_auto_approve: "建议自动批准",
  would_append_evidence: "建议追加证据",
  would_auto_reject_noise: "建议拒绝低价值噪声",
  requires_owner_review: "必须主人审核",
  blocked: "已阻止",
}[value] ?? value || "未知");

const riskTone = (risk: string): "good" | "warn" | "bad" | undefined =>
  risk === "low" ? "good" : risk === "medium" ? "warn" : risk === "high" || risk === "critical" ? "bad" : undefined;

type DashboardData = {
  status: AutoReviewStatus;
  metrics: AutoReviewMetrics;
  decisions: AutoReviewDecisionPage;
};

export default function AutoReviewPage({ api, active }: PageProps) {
  const [selected, setSelected] = useState<AutoReviewAudit | null>(null);
  const [candidateId, setCandidateId] = useState("");
  const [feedbackOutcome, setFeedbackOutcome] = useState("owner_agreed");
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [actionState, setActionState] = useState("");
  const [actionError, setActionError] = useState("");

  const load = useCallback(async (signal: AbortSignal): Promise<DashboardData> => {
    const [status, metrics, decisions] = await Promise.all([
      api.get<AutoReviewStatus>("/api/auto-review/status", { signal }),
      api.get<AutoReviewMetrics>("/api/auto-review/metrics", { signal }),
      api.get<AutoReviewDecisionPage>("/api/auto-review/decisions?limit=200", { signal }),
    ]);
    return { status, metrics, decisions };
  }, [api]);

  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 8_000,
    staleAfterMs: 25_000,
    pauseWhenHidden: true,
  });

  const rows = useMemo(() => resource.data?.decisions.items ?? [], [resource.data]);
  const ownerReviewCount = resource.data?.metrics.actions.requires_owner_review ?? 0;
  const blockedCount = resource.data?.metrics.actions.blocked ?? 0;

  async function evaluateCandidate() {
    const id = candidateId.trim();
    if (!id || actionState) return;
    setActionState("evaluate");
    setActionError("");
    try {
      const candidate = await api.get<Row>(`/api/memory/review/candidates/${encodeURIComponent(id)}`);
      const result = await api.post<AutoReviewAudit>(
        `/api/auto-review/evaluate/${encodeURIComponent(id)}`,
        {
          candidate,
          context: {
            mode: "SHADOW",
            evidence_sufficient: Array.isArray(candidate.source_refs) && candidate.source_refs.length > 0,
            owner_authored: candidate.proposed_by === "owner" || candidate.proposed_by === "owner_manual",
          },
        },
      );
      setSelected(result);
      await resource.refresh();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setActionState("");
    }
  }

  async function submitFeedback() {
    if (!selected?.decision.decision_id || actionState) return;
    setActionState("feedback");
    setActionError("");
    try {
      await api.post("/api/auto-review/feedback", {
        decision_id: selected.decision.decision_id,
        outcome: feedbackOutcome,
        notes: feedbackNotes,
      });
      setFeedbackNotes("");
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setActionState("");
    }
  }

  if (!active) return <Empty text="连接本机服务后显示 Auto Review SHADOW 看板。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取 Auto Review 状态..." />;
  if (resource.error && !resource.data) {
    return <Notice kind="error">Auto Review API 暂不可用：{resource.error.message}</Notice>;
  }

  const data = resource.data;
  const status = data?.status;
  const metrics = data?.metrics;
  const modeTruthful = status?.mode || "未知";

  return (
    <div className="stack auto-review-page">
      <Notice kind="warning">
        <strong>SHADOW 只记录“如果允许自动化会怎么建议”。</strong>
        它不会批准、拒绝、合并、删除或写入长期记忆。真正改变记忆仍只能在“人工记忆审核”中由主人确认。
      </Notice>
      {modeTruthful === "ACTIVE" && (
        <Notice kind="error">检测到不受支持的 ACTIVE 状态。当前版本必须阻止执行并恢复为 OFF 或 SHADOW。</Notice>
      )}
      {resource.error && data && <Notice kind="error">刷新失败：{resource.error.message}。以下为最近一次成功数据。</Notice>}
      <div className="toolbar">
        <button className="button secondary" disabled={resource.refreshing} onClick={() => void resource.refresh()}>
          {resource.refreshing ? "刷新中..." : "刷新看板"}
        </button>
        <span>模式 {modeTruthful}</span>
        <span>{resource.stale ? "数据已过期" : "数据为最近状态"}</span>
        <span>变更执行数 {metrics?.mutation_count ?? "未知"}</span>
      </div>

      <div className="metric-grid">
        <Metric title="运行模式" value={modeTruthful} detail={status?.mutation_enabled ? "异常：允许变更" : "只观察，不执行"} tone={status?.mutation_enabled || modeTruthful === "ACTIVE" ? "bad" : modeTruthful === "SHADOW" ? "warn" : undefined} />
        <Metric title="SHADOW 决策" value={metrics?.total == null ? "未知" : String(metrics.total)} detail={`AI 参与 ${metrics?.ai_assessed ?? "未知"}`} />
        <Metric title="主人审核" value={String(ownerReviewCount)} detail={`阻止 ${blockedCount}`} tone={ownerReviewCount || blockedCount ? "warn" : "good"} />
        <Metric title="实际记忆变更" value={metrics?.mutation_count == null ? "未知" : String(metrics.mutation_count)} detail="正确值应始终为 0" tone={metrics?.mutation_count === 0 ? "good" : "bad"} />
      </div>

      <div className="two-column wide-left">
        <Panel title="决策记录">
          {rows.length ? (
            <DataTable
              headers={["时间", "候选", "建议", "风险", "评分", "AI", "变更"]}
              rows={rows.map((item) => [
                String(item.evaluated_at ?? "").slice(0, 19),
                item.decision.candidate_id,
                <button className="decision-link" onClick={() => setSelected(item)}>{actionLabel(item.decision.action)}</button>,
                item.decision.risk_level,
                item.decision.risk_score,
                item.ai_assessment?.available ? item.ai_assessment.model || "本地模型" : "未使用/不可用",
                item.decision.mutation_performed ? "异常：已执行" : "未执行",
              ] as React.ReactNode[])}
            />
          ) : <Empty text="尚无 SHADOW 决策。可以输入候选记忆 ID 做一次只读评估。" />}
        </Panel>

        <Panel title="只读评估">
          <div className="auto-review-form">
            <label>
              候选记忆 ID
              <input value={candidateId} onChange={(event) => setCandidateId(event.target.value)} placeholder="LJ-MEM-..." />
            </label>
            <button className="button secondary" disabled={!candidateId.trim() || Boolean(actionState)} onClick={() => void evaluateCandidate()}>
              {actionState === "evaluate" ? "评估中..." : "运行 SHADOW 评估"}
            </button>
            <small>只读取候选内容并写入审计建议，不会调用批准、拒绝或生命周期接口。</small>
          </div>
          {actionError && <Notice kind="error">{actionError}</Notice>}
        </Panel>
      </div>

      <Panel title="决策解释">
        {selected ? (
          <div className="auto-review-detail">
            <div className="metric-grid compact">
              <Metric title="建议" value={actionLabel(selected.decision.action)} />
              <Metric title="风险" value={selected.decision.risk_level} detail={`评分 ${selected.decision.risk_score}`} tone={riskTone(selected.decision.risk_level)} />
              <Metric title="可逆" value={selected.decision.reversible ? "是" : "否"} />
              <Metric title="是否执行" value={selected.decision.mutation_performed ? "已执行（异常）" : "未执行"} tone={selected.decision.mutation_performed ? "bad" : "good"} />
            </div>
            <div className="list">
              {selected.decision.reasons.map((reason) => (
                <div className="list-row" key={`${selected.decision.decision_id}:${reason.code}`}>
                  <span className={`pill ${reason.blocked ? "error" : reason.hard_manual ? "warning" : "success"}`}>{reason.risk_points}</span>
                  <div><strong>{reason.code}</strong><small>{reason.message}</small></div>
                </div>
              ))}
            </div>
            {selected.ai_assessment && (
              <Notice>
                本地 AI：{selected.ai_assessment.available ? selected.ai_assessment.summary || "已增加风险" : selected.ai_assessment.error || "不可用"}
              </Notice>
            )}
            <div className="auto-review-feedback">
              <select value={feedbackOutcome} onChange={(event) => setFeedbackOutcome(event.target.value)}>
                <option value="owner_agreed">主人同意建议</option>
                <option value="owner_disagreed">主人不同意建议</option>
                <option value="needs_more_evidence">需要更多证据</option>
                <option value="false_positive">误判</option>
              </select>
              <input value={feedbackNotes} onChange={(event) => setFeedbackNotes(event.target.value)} placeholder="反馈备注（可选）" />
              <button className="button secondary" disabled={Boolean(actionState)} onClick={() => void submitFeedback()}>
                {actionState === "feedback" ? "记录中..." : "记录主人反馈"}
              </button>
            </div>
          </div>
        ) : <Empty text="选择一条决策查看每条规则、风险和本地 AI 摘要。" />}
      </Panel>
    </div>
  );
}
