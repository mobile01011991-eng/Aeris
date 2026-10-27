import { Link } from "react-router-dom";
import { reportStatusKey, type ToolView } from "../api/reports";
import { useI18n } from "../i18n/I18nContext";

export function ToolReportCard({
  view,
  sampleId,
  jobId,
}: {
  view: ToolView;
  sampleId: string;
  jobId?: string | null;
}) {
  const { t } = useI18n();
  const openable = Boolean(view.report);
  const to = `/results/${encodeURIComponent(sampleId)}/${view.key}${
    jobId ? `?job=${encodeURIComponent(jobId)}` : ""
  }`;

  const counts = view.report
    ? t("card.counts", {
        passed: view.report.filtered_hit_count,
        total: view.report.hit_count,
      })
    : view.detail || t("card.waiting");

  return (
    <article
      className={`report-card ${view.kind === "ai" ? "ai" : "db"} ${view.status}`}
    >
      <div className="report-card-top">
        <h3>{view.label}</h3>
        <span className={`flow-chip ${view.status}`}>
          {t(reportStatusKey(view.status))}
        </span>
      </div>

      {view.kind === "ai" && <p className="ai-badge">{t("card.aiBadge")}</p>}

      <p className="report-card-blurb">{t(view.blurbKey)}</p>

      <p className="muted report-card-counts">
        {view.status === "failed"
          ? view.report?.error || view.detail || t("card.failed")
          : counts}
      </p>

      {openable ? (
        <Link className="btn btn-ghost report-card-open" to={to}>
          {t("card.open")}
        </Link>
      ) : (
        <span className="btn btn-ghost report-card-open" aria-disabled="true">
          {view.status === "running" ? t("card.running") : t("card.notReady")}
        </span>
      )}
    </article>
  );
}
