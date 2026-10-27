import { HitTable } from "../HitTable";
import { pct, plain } from "../../api/reports";
import { useI18n } from "../../i18n/I18nContext";
import type { AmrFinderRow, ToolReport } from "../../api/types";

function ElementTable({ rows }: { rows: AmrFinderRow[] }) {
  const { t } = useI18n();

  return (
    <div className="table-wrap">
      <table className="consensus-table hit-detail-table">
        <thead>
          <tr>
            <th>{t("amr.col.element")}</th>
            <th>{t("table.drugClass")}</th>
            <th>{t("amr.col.subclass")}</th>
            <th>{t("amr.col.method")}</th>
            <th>{t("table.identity")}</th>
            <th>{t("table.coverage")}</th>
            <th>{t("table.contig")}</th>
            <th>{t("amr.col.closestRef")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={`${row.element_symbol}-${i}`}>
              <td>
                <strong>{plain(row.element_symbol)}</strong>
                {row.element_name && (
                  <div className="muted">{row.element_name}</div>
                )}
              </td>
              <td>{plain(row.drug_class)}</td>
              <td>{plain(row.subclass)}</td>
              <td>
                <span className="tag">{plain(row.method)}</span>
              </td>
              <td>{pct(row.identity)}</td>
              <td>{pct(row.coverage)}</td>
              <td className="mono">{plain(row.contig)}</td>
              <td className="mono">{plain(row.accession)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AmrFinderReport({
  report,
  idMin,
  covMin,
}: {
  report: ToolReport;
  idMin: number;
  covMin: number;
}) {
  const { t } = useI18n();
  const amr = (report.extras?.amr ?? []) as AmrFinderRow[];
  const point = (report.extras?.point ?? []) as AmrFinderRow[];
  const other = (report.extras?.other ?? []) as AmrFinderRow[];
  const hasNative = amr.length > 0 || point.length > 0 || other.length > 0;

  return (
    <>
      <section className="panel">
        <h2 className="section-title report-section-title">{t("amr.title")}</h2>
        <p className="section-lead">{t("amr.lead")}</p>

        {!hasNative ? (
          <>
            <p className="section-lead">{t("amr.fallbackLead")}</p>
            <HitTable hits={report.hits} idMin={idMin} covMin={covMin} />
          </>
        ) : amr.length === 0 ? (
          <p className="section-lead">{t("amr.empty")}</p>
        ) : (
          <ElementTable rows={amr} />
        )}
      </section>

      {point.length > 0 && (
        <section className="panel report-block">
          <h2 className="section-title report-section-title">
            {t("amr.point.title")}
          </h2>
          <p className="section-lead">{t("amr.point.lead")}</p>
          <ElementTable rows={point} />
        </section>
      )}

      {other.length > 0 && (
        <section className="panel report-block">
          <h2 className="section-title report-section-title">
            {t("amr.other.title")}
          </h2>
          <p className="section-lead">{t("amr.other.lead")}</p>
          <ElementTable rows={other} />
        </section>
      )}
    </>
  );
}
