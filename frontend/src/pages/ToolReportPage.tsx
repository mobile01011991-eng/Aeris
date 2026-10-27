import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  buildToolViews,
  findToolView,
  geneFamily,
  passesFilter,
  toolMeta,
} from "../api/reports";
import { useSampleReports } from "../api/useSampleReports";
import { useI18n } from "../i18n/I18nContext";
import { SampleContextPanel } from "../components/SampleContextPanel";
import { AbricateReport } from "../components/reports/AbricateReport";
import { AmrFinderReport } from "../components/reports/AmrFinderReport";
import { DeepArgReport } from "../components/reports/DeepArgReport";
import { ResFinderReport } from "../components/reports/ResFinderReport";
import { RgiReport } from "../components/reports/RgiReport";

export function ToolReportPage() {
  const { sampleId = "", toolKey = "" } = useParams();
  const [params] = useSearchParams();
  const jobId = params.get("job");
  const { t } = useI18n();

  const { job, payload, error, loading } = useSampleReports(sampleId, jobId);
  const views = buildToolViews(job, payload);
  const view = findToolView(views, toolKey);
  const meta = toolMeta(toolKey);

  const idMin = payload?.filter_thresholds?.sequence_identity_min ?? 90;
  const covMin = payload?.filter_thresholds?.coverage_percentage_min ?? 80;

  const hubLink = `/results/${encodeURIComponent(sampleId)}${
    jobId ? `?job=${encodeURIComponent(jobId)}` : ""
  }`;

  // Families called by the database tools — used only to flag AI-only rows.
  const databaseFamilies = new Set<string>();
  views
    .filter((v) => v.kind !== "ai")
    .forEach((v) =>
      v.report?.hits
        .filter((hit) => passesFilter(hit, idMin, covMin))
        .forEach((hit) => {
          const family = geneFamily(hit.gene_symbol);
          if (family) databaseFamilies.add(family);
        }),
    );

  const report = view?.report;

  function renderReport() {
    if (!report) return null;
    switch (toolKey) {
      case "resfinder":
        return (
          <ResFinderReport report={report} idMin={idMin} covMin={covMin} />
        );
      case "rgi":
        return <RgiReport report={report} idMin={idMin} covMin={covMin} />;
      case "amrfinderplus":
        return (
          <AmrFinderReport report={report} idMin={idMin} covMin={covMin} />
        );
      case "abricate":
        return <AbricateReport report={report} idMin={idMin} covMin={covMin} />;
      case "deeparg":
        return (
          <DeepArgReport report={report} databaseFamilies={databaseFamilies} />
        );
      default:
        return (
          <div className="panel">
            <p className="section-lead">
              {t("toolPage.noView", { tool: toolKey })}
            </p>
          </div>
        );
    }
  }

  return (
    <section className="section">
      <div className="results-header">
        <div>
          <p className="eyebrow">
            <Link to={hubLink}>{t("toolPage.back")}</Link>
          </p>
          <h1 className="section-title">{view?.label || meta.label}</h1>
          <p className="section-lead" style={{ marginBottom: 0 }}>
            <span className={`tag ${meta.kind === "ai" ? "ai-tag" : ""}`}>
              {meta.kind === "ai"
                ? t("toolPage.badge.ai")
                : t("toolPage.badge.database")}
            </span>{" "}
            {t("hub.sample")} <strong>{sampleId}</strong>
          </p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn btn-ghost" to={hubLink}>
            {t("toolPage.backBtn")}
          </Link>
        </div>
      </div>

      <SampleContextPanel
        payload={payload}
        job={job}
        idMin={idMin}
        covMin={covMin}
      />

      <div className="report-block">
        {loading && !view && (
          <p className="busy">
            <span className="spinner" /> {t("toolPage.loading")}
          </p>
        )}

        {!loading && !view && (
          <div className="panel">
            <p className="section-lead">
              {t("toolPage.notInRun", { tool: toolKey })}
            </p>
            <Link className="btn btn-ghost" to={hubLink}>
              {t("toolPage.backBtn")}
            </Link>
          </div>
        )}

        {view && !report && (
          <div className="panel">
            <p className="section-lead">
              {view.status === "running"
                ? t("toolPage.stillRunning")
                : view.status === "failed"
                  ? t("toolPage.failedNoReport")
                  : t("toolPage.notRunYet")}
            </p>
            {view.detail && <p className="muted">{view.detail}</p>}
          </div>
        )}

        {view && report && !report.success && (
          <div className="error-banner">
            {report.error || t("toolPage.failedBanner")}
          </div>
        )}

        {report?.extras?.demo && (
          <p className="hint-row">{t("toolPage.demoNote")}</p>
        )}

        {renderReport()}

        {error && !view && <div className="error-banner">{error}</div>}
      </div>
    </section>
  );
}
