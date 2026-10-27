import { HitTable } from "../HitTable";
import { pct, plain } from "../../api/reports";
import { useI18n } from "../../i18n/I18nContext";
import type { AbricateRow, ToolReport } from "../../api/types";

export function AbricateReport({
  report,
  idMin,
  covMin,
}: {
  report: ToolReport;
  idMin: number;
  covMin: number;
}) {
  const { t } = useI18n();
  const rows = (report.extras?.hits ?? []) as AbricateRow[];

  if (!rows.length) {
    return (
      <section className="panel">
        <h2 className="section-title report-section-title">
          {t("abricate.title")}
        </h2>
        <p className="section-lead">{t("abricate.fallbackLead")}</p>
        <HitTable hits={report.hits} idMin={idMin} covMin={covMin} />
      </section>
    );
  }

  return (
    <section className="panel">
      <h2 className="section-title report-section-title">
        {t("abricate.title")}
      </h2>
      <p className="section-lead">{t("abricate.lead")}</p>

      <div className="table-wrap">
        <table className="consensus-table hit-detail-table">
          <thead>
            <tr>
              <th>{t("table.gene")}</th>
              <th>{t("table.contig")}</th>
              <th>{t("abricate.col.position")}</th>
              <th>{t("table.identity")}</th>
              <th>{t("table.coverage")}</th>
              <th>{t("table.accession")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={`${row.gene}-${i}`}>
                <td>
                  <strong>{plain(row.gene_display || row.gene)}</strong>
                  {row.gene !== row.gene_display && (
                    <div className="muted mono">{row.gene}</div>
                  )}
                </td>
                <td className="mono">{plain(row.contig)}</td>
                <td className="mono">
                  {row.start && row.end ? `${row.start}–${row.end}` : "—"}
                </td>
                <td>{pct(row.identity)}</td>
                <td>{pct(row.coverage)}</td>
                <td className="mono">{plain(row.accession)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="hint-row">{t("abricate.note")}</p>
    </section>
  );
}
