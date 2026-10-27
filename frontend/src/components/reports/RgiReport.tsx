import { HitTable } from "../HitTable";
import { pct, plain } from "../../api/reports";
import { useI18n } from "../../i18n/I18nContext";
import type { RgiRow, ToolReport } from "../../api/types";

export function RgiReport({
  report,
  idMin,
  covMin,
}: {
  report: ToolReport;
  idMin: number;
  covMin: number;
}) {
  const { t } = useI18n();
  const rows = (report.extras?.hits ?? []) as RgiRow[];

  if (!rows.length) {
    return (
      <section className="panel">
        <h2 className="section-title report-section-title">{t("rgi.title")}</h2>
        <p className="section-lead">{t("rgi.fallbackLead")}</p>
        <HitTable hits={report.hits} idMin={idMin} covMin={covMin} />
      </section>
    );
  }

  return (
    <section className="panel">
      <h2 className="section-title report-section-title">{t("rgi.title")}</h2>
      <p className="section-lead">{t("rgi.lead")}</p>

      <div className="table-wrap">
        <table className="consensus-table hit-detail-table">
          <thead>
            <tr>
              <th>{t("rgi.col.bestHit")}</th>
              <th>{t("rgi.col.cutOff")}</th>
              <th>{t("table.identity")}</th>
              <th>{t("rgi.col.refLength")}</th>
              <th>{t("rgi.col.mechanism")}</th>
              <th>{t("rgi.col.family")}</th>
              <th>{t("table.drugClass")}</th>
              <th>{t("table.contig")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={`${row.best_hit_aro}-${i}`}>
                <td>
                  <strong>{plain(row.best_hit_aro)}</strong>
                  {row.aro && (
                    <div className="muted">{t("rgi.aro", { id: row.aro })}</div>
                  )}
                </td>
                <td>
                  <span
                    className={`status-chip ${
                      /perfect/i.test(row.cut_off || "")
                        ? "susceptible"
                        : "ambiguous"
                    }`}
                  >
                    {plain(row.cut_off)}
                  </span>
                </td>
                <td>{pct(row.identity)}</td>
                <td>{pct(row.percent_length)}</td>
                <td>{plain(row.resistance_mechanism)}</td>
                <td>{plain(row.amr_gene_family)}</td>
                <td>{plain(row.drug_class)}</td>
                <td className="mono">{plain(row.contig)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="report-legend">
        <li>{t("rgi.legend.perfect")}</li>
        <li>{t("rgi.legend.strict")}</li>
      </ul>
    </section>
  );
}
