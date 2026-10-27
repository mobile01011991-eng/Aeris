import { geneFamily, pct, plain } from "../../api/reports";
import { useI18n } from "../../i18n/I18nContext";
import type { DeepArgRow, ToolReport } from "../../api/types";

function probability(value?: number | null): string {
  if (value == null) return "—";
  return `${Math.round(value * 1000) / 10}%`;
}

export function DeepArgReport({
  report,
  databaseFamilies,
}: {
  report: ToolReport;
  /** Families seen by the four database tools, used only to flag AI-only calls. */
  databaseFamilies: Set<string>;
}) {
  const { t } = useI18n();
  const rows = (report.extras?.predictions ?? []) as DeepArgRow[];
  const fallbackRows: DeepArgRow[] = report.hits.map((hit) => ({
    gene_family: geneFamily(hit.gene_symbol),
    predicted_class: String(hit.drug_class ?? ""),
    probability: null,
    identity:
      hit.sequence_identity == null ? null : Number(hit.sequence_identity),
    contig: String(hit.input_sequence_id ?? ""),
  }));
  const predictions = rows.length ? rows : fallbackRows;

  return (
    <section className="panel ai-panel">
      <p className="ai-badge">{t("card.aiBadge")}</p>
      <h2 className="section-title report-section-title">
        {t("deeparg.title")}
      </h2>
      <p className="section-lead">{t("deeparg.lead")}</p>

      {predictions.length === 0 ? (
        <p className="section-lead">{t("deeparg.empty")}</p>
      ) : (
        <div className="table-wrap">
          <table className="consensus-table hit-detail-table">
            <thead>
              <tr>
                <th>{t("deeparg.col.family")}</th>
                <th>{t("deeparg.col.class")}</th>
                <th>{t("deeparg.col.probability")}</th>
                <th>{t("deeparg.col.identity")}</th>
                <th>{t("table.contig")}</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((row, i) => {
                const family = (row.gene_family || "").toUpperCase();
                const aiOnly = family !== "" && !databaseFamilies.has(family);
                return (
                  <tr key={`${row.gene_family}-${i}`}>
                    <td>
                      <strong>{plain(row.gene_family)}</strong>
                      {aiOnly && (
                        <div>
                          <span className="status-chip ambiguous">
                            {t("deeparg.aiOnly")}
                          </span>
                        </div>
                      )}
                    </td>
                    <td>{plain(row.predicted_class)}</td>
                    <td>{probability(row.probability)}</td>
                    <td>{pct(row.identity)}</td>
                    <td className="mono">
                      {plain(String(row.contig ?? "").split(/\s+/)[0])}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="hint-row">{t("deeparg.note")}</p>
    </section>
  );
}
