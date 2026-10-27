import { useI18n } from "../i18n/I18nContext";
import type { AnalysisJob } from "../api/client";

type Decision = "accept_system" | "keep_user" | "cancel";

export function OrganismConfirmModal({
  job,
  busy,
  onDecide,
}: {
  job: AnalysisJob;
  busy?: boolean;
  onDecide: (decision: Decision) => void;
}) {
  const { t } = useI18n();
  const match = job.species_report?.match;
  const declared =
    match?.declared_name || job.declared_organism || "—";
  const detected = job.detected_organism || match?.detected_name || "—";
  const confidence =
    typeof match?.confidence === "number"
      ? `${Math.round(match.confidence * 100)}%`
      : "—";
  const status = match?.match_status || "mismatch";

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-panel organism-modal">
        <p className="eyebrow">{t("organism.eyebrow")}</p>
        <h2 className="modal-title">{t("organism.title")}</h2>
        <p className="muted">{t("organism.body")}</p>

        <div className="organism-compare">
          <div>
            <span className="stat-label">{t("organism.youSelected")}</span>
            <strong>{declared}</strong>
          </div>
          <div>
            <span className="stat-label">{t("organism.detected")}</span>
            <strong>{detected}</strong>
          </div>
          <div>
            <span className="stat-label">{t("organism.status")}</span>
            <strong className="organism-status">{status}</strong>
          </div>
          <div>
            <span className="stat-label">{t("organism.confidence")}</span>
            <strong>{confidence}</strong>
          </div>
        </div>

        {match?.reason && <p className="hint-row">{match.reason}</p>}

        <div className="actions modal-actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || !job.detected_organism}
            onClick={() => onDecide("accept_system")}
          >
            {t("organism.accept")}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={busy}
            onClick={() => onDecide("keep_user")}
          >
            {t("organism.keep")}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={busy}
            onClick={() => onDecide("cancel")}
          >
            {t("organism.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
