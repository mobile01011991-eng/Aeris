import { Link, useParams, useSearchParams } from "react-router-dom";
import { isTerminalJob } from "../api/client";
import { buildToolViews, splitToolViews } from "../api/reports";
import { useSampleReports } from "../api/useSampleReports";
import { useI18n } from "../i18n/I18nContext";
import type { TranslationKey } from "../i18n/translations";
import type { AMRResultPayload } from "../api/types";
import { AgreementPanel } from "../components/AgreementPanel";
import { PipelineProgress } from "../components/PipelineProgress";
import { SampleContextPanel } from "../components/SampleContextPanel";
import { ToolReportCard } from "../components/ToolReportCard";

function downloadJson(payload: AMRResultPayload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${payload.sample_id}_aeris_tool_reports.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export function ResultsHubPage() {
  const { sampleId = "" } = useParams();
  const [params] = useSearchParams();
  const jobId = params.get("job");
  const { t } = useI18n();

  const { job, payload, error, loading } = useSampleReports(sampleId, jobId);
  const views = buildToolViews(job, payload);
  const { database, ai } = splitToolViews(views);

  const idMin = payload?.filter_thresholds?.sequence_identity_min ?? 90;
  const covMin = payload?.filter_thresholds?.coverage_percentage_min ?? 80;

  const running = job != null && !isTerminalJob(job);
  const isDemo =
    job?.mode === "demo" ||
    views.some((v) => v.report?.extras?.demo === true);

  return (
    <section className="section">
      <div className="results-header">
        <div>
          <p className="eyebrow">{t("hub.eyebrow")}</p>
          <h1 className="section-title">{t("hub.title")}</h1>
          <p className="section-lead" style={{ marginBottom: 0 }}>
            {t("hub.sample")} <strong>{sampleId}</strong>
            {job && (
              <>
                {" · "}
                {t("hub.jobStatus", {
                  status: t(`job.status.${job.status}` as TranslationKey),
                })}
              </>
            )}
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn btn-ghost" to="/">
            {t("hub.newAnalysis")}
          </Link>
          {payload && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => downloadJson(payload)}
            >
              {t("hub.download")}
            </button>
          )}
        </div>
      </div>

      {loading && !views.length && (
        <p className="busy">
          <span className="spinner" /> {t("hub.loading")}
        </p>
      )}
      {error && !views.length && <div className="error-banner">{error}</div>}
      {job?.error && <div className="error-banner">{job.error}</div>}

      {job?.status === "awaiting_organism_confirmation" && (
        <div className="error-banner">
          {t("hub.awaiting")} <Link to="/">{t("hub.awaiting.link")}</Link>{" "}
          {t("hub.awaiting.tail")}
        </div>
      )}

      {isDemo && <p className="hint-row">{t("hub.demoNote")}</p>}

      <SampleContextPanel
        payload={payload}
        job={job}
        idMin={idMin}
        covMin={covMin}
      />

      {running && job && (
        <div className="report-block">
          <PipelineProgress steps={job.steps} jobStatus={job.status} />
        </div>
      )}

      <div className="report-block">
        <h2 className="section-title report-section-title">
          {t("hub.database.title")}
        </h2>
        <p className="section-lead">{t("hub.database.lead")}</p>
        <div className="report-card-grid">
          {database.map((view) => (
            <ToolReportCard
              key={view.key}
              view={view}
              sampleId={sampleId}
              jobId={jobId}
            />
          ))}
        </div>
      </div>

      {ai.length > 0 && (
        <div className="report-block">
          <h2 className="section-title report-section-title">
            {t("hub.ai.title")}
          </h2>
          <p className="section-lead">{t("hub.ai.lead")}</p>
          <div className="report-card-grid ai-grid">
            {ai.map((view) => (
              <ToolReportCard
                key={view.key}
                view={view}
                sampleId={sampleId}
                jobId={jobId}
              />
            ))}
          </div>
        </div>
      )}

      <div className="report-block">
        <AgreementPanel views={views} idMin={idMin} covMin={covMin} />
      </div>

      <p className="hint-row">{t("hub.disclaimer")}</p>
    </section>
  );
}
