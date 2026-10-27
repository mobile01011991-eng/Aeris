import { pct, plain } from "../../api/reports";
import { useI18n } from "../../i18n/I18nContext";
import type { PointFinderStatus, PointMutationRow } from "../../api/types";

/**
 * Chromosomal point mutations from ResFinder's PointFinder module.
 *
 * PointFinder only runs for species that have a panel in the database, so the
 * empty states have to say which case applies — an empty table is not the same
 * as an unsupported organism.
 */
export function PointFinderSection({
  status,
  species,
  reason,
  mutations,
}: {
  status?: PointFinderStatus;
  species?: string | null;
  reason?: string;
  mutations: PointMutationRow[];
}) {
  const { t } = useI18n();
  const state: PointFinderStatus = status ?? "skipped";

  return (
    <section className="panel report-block">
      <h2 className="section-title report-section-title">
        {t("pointfinder.title")}
      </h2>
      <p className="section-lead">{t("pointfinder.lead")}</p>

      {state === "failed" && (
        <div className="error-banner">
          {t("pointfinder.failed")}
          {reason ? ` ${reason}` : ""}
        </div>
      )}

      {state === "skipped" && (
        <p className="section-lead">
          {t("pointfinder.skipped")}
          {reason ? ` (${reason})` : ""}
        </p>
      )}

      {state === "ran" && species && (
        <p className="muted">{t("pointfinder.species", { species })}</p>
      )}

      {state === "ran" && mutations.length === 0 && (
        <p className="section-lead">{t("pointfinder.noHits")}</p>
      )}

      {mutations.length > 0 && (
        <div className="table-wrap">
          <table className="consensus-table hit-detail-table">
            <thead>
              <tr>
                <th>{t("table.gene")}</th>
                <th>{t("pointfinder.col.mutation")}</th>
                <th>{t("pointfinder.col.change")}</th>
                <th>{t("pointfinder.col.antimicrobials")}</th>
                <th>{t("table.identity")}</th>
                <th>{t("table.coverage")}</th>
                <th>{t("table.contig")}</th>
              </tr>
            </thead>
            <tbody>
              {mutations.map((row, i) => (
                <tr key={`${row.gene}-${row.mutation}-${i}`}>
                  <td>
                    <strong>{plain(row.gene)}</strong>
                    {row.variation_type && (
                      <div className="muted">{row.variation_type}</div>
                    )}
                  </td>
                  <td>
                    <strong>{plain(row.mutation)}</strong>
                    {row.codon_position != null && (
                      <div className="muted">
                        {t("pointfinder.codon", { position: row.codon_position })}
                      </div>
                    )}
                  </td>
                  <td>
                    {plain(row.nucleotide_change)}
                    {row.amino_acid_change && (
                      <div className="muted">{row.amino_acid_change}</div>
                    )}
                  </td>
                  <td>
                    {row.antimicrobials?.length ? (
                      <div className="tool-list">
                        {row.antimicrobials.map((agent) => (
                          <span className="tag" key={agent}>
                            {agent}
                          </span>
                        ))}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>{pct(row.identity)}</td>
                  <td>{pct(row.coverage)}</td>
                  <td className="mono">{plain(row.contig)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="hint-row">{t("pointfinder.note")}</p>
    </section>
  );
}
