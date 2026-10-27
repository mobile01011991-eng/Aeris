import { plain } from "../api/reports";
import { useI18n } from "../i18n/I18nContext";
import type { AnalysisJob } from "../api/client";
import type { AMRResultPayload } from "../api/types";

export function SampleContextPanel({
  payload,
  job,
  idMin,
  covMin,
}: {
  payload: AMRResultPayload | null;
  job: AnalysisJob | null;
  idMin: number;
  covMin: number;
}) {
  const { t } = useI18n();
  const organism = payload?.organism;
  const confirmed = organism?.confirmed || job?.confirmed_organism;
  const declared = organism?.declared || job?.declared_organism;
  const detected = organism?.detected || job?.detected_organism;
  const decision = organism?.decision || job?.organism_decision;

  return (
    <div className="panel organism-result-panel sample-context">
      <div className="organism-compare">
        <div>
          <span className="stat-label">{t("context.organism")}</span>
          <strong>{plain(confirmed)}</strong>
        </div>
        <div>
          <span className="stat-label">{t("context.declaredDetected")}</span>
          <strong>
            {plain(declared)} · {plain(detected)}
          </strong>
        </div>
        <div>
          <span className="stat-label">{t("context.decision")}</span>
          <strong>{plain(decision)}</strong>
        </div>
        <div>
          <span className="stat-label">{t("context.filters")}</span>
          <strong>
            ID ≥ {idMin}% · Cov ≥ {covMin}%
          </strong>
        </div>
      </div>

      {organism?.warning && (
        <div className="error-banner" style={{ marginTop: "0.9rem" }}>
          {organism.warning}
        </div>
      )}
    </div>
  );
}
