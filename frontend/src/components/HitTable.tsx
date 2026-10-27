import { contigOf, passesFilter, pct, plain } from "../api/reports";
import { useI18n } from "../i18n/I18nContext";
import type { HarmonizedHit } from "../api/types";

/**
 * Shared hAMRonized subset — the fields every tool reports.
 *
 * Tool-specific columns live in each tool's own report component.
 */
export function HitTable({
  hits,
  idMin,
  covMin,
  emptyMessage,
}: {
  hits: HarmonizedHit[];
  idMin: number;
  covMin: number;
  emptyMessage?: string;
}) {
  const { t } = useI18n();

  if (!hits.length) {
    return <p className="section-lead">{emptyMessage ?? t("table.empty")}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="consensus-table hit-detail-table">
        <thead>
          <tr>
            <th>{t("table.gene")}</th>
            <th>{t("table.drugClass")}</th>
            <th>{t("table.identity")}</th>
            <th>{t("table.coverage")}</th>
            <th>{t("table.contig")}</th>
            <th>{t("table.accession")}</th>
            <th>{t("table.filter")}</th>
          </tr>
        </thead>
        <tbody>
          {hits.map((hit, i) => {
            const ok = passesFilter(hit, idMin, covMin);
            return (
              <tr key={`${hit.gene_symbol ?? "hit"}-${i}`}>
                <td>
                  <strong>{plain(hit.gene_symbol)}</strong>
                  {hit.gene_name && hit.gene_name !== hit.gene_symbol && (
                    <div className="muted">{hit.gene_name}</div>
                  )}
                </td>
                <td>{plain(hit.normalized_drug_class || hit.drug_class)}</td>
                <td>{pct(hit.sequence_identity)}</td>
                <td>{pct(hit.coverage_percentage)}</td>
                <td className="mono">{contigOf(hit)}</td>
                <td className="mono">{plain(hit.reference_accession)}</td>
                <td>
                  <span
                    className={`status-chip ${ok ? "susceptible" : "ambiguous"}`}
                  >
                    {ok ? t("table.pass") : t("table.fail")}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
