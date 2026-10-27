import { useMemo, useState } from "react";
import { contigOf, passesFilter, pct, plain } from "../../api/reports";
import { useI18n } from "../../i18n/I18nContext";
import type {
  HarmonizedHit,
  PointMutationRow,
  ResFinderPhenotypeRow,
  ToolReport,
} from "../../api/types";
import { PointFinderSection } from "./PointFinderSection";

/**
 * With PointFinder enabled, hAMRonize adds the chromosomal mutations to the
 * same hit list. They belong in their own section, not in the acquired-gene
 * table, so drop anything reported as a sequence variant.
 */
function isAcquiredGeneHit(hit: HarmonizedHit): boolean {
  const variationType = String(hit.genetic_variation_type ?? "");
  if (variationType.includes("variant")) return false;
  if (String(hit.reference_database_name ?? "") === "PointFinder") return false;
  return !hit.amino_acid_mutation && !hit.nucleotide_mutation;
}

const MATCH_LEGEND_KEYS = [
  "resfinder.legend.0",
  "resfinder.legend.1",
  "resfinder.legend.2",
  "resfinder.legend.3",
] as const;

export function ResFinderReport({
  report,
  idMin,
  covMin,
}: {
  report: ToolReport;
  idMin: number;
  covMin: number;
}) {
  const { t } = useI18n();
  const [showAllAgents, setShowAllAgents] = useState(false);

  // Several alleles can hit the same contig (blaTEM-1B vs blaTEM-104); those
  // are alternative calls for one locus, not separate genes.
  const contigGroups = useMemo(() => {
    const groups = new Map<string, HarmonizedHit[]>();
    report.hits.filter(isAcquiredGeneHit).forEach((hit) => {
      const contig = contigOf(hit);
      const bucket = groups.get(contig) ?? [];
      bucket.push(hit);
      groups.set(contig, bucket);
    });
    return [...groups.entries()];
  }, [report.hits]);

  const phenotypes = (report.extras?.phenotypes ?? []) as ResFinderPhenotypeRow[];
  const resistantRows = phenotypes.filter(
    (row) => !/^no resistance$/i.test(row.phenotype),
  );
  const visibleRows = showAllAgents ? phenotypes : resistantRows;

  return (
    <>
      <section className="panel">
        <h2 className="section-title report-section-title">
          {t("resfinder.genes.title")}
        </h2>
        <p className="section-lead">{t("resfinder.genes.lead")}</p>

        {contigGroups.length === 0 ? (
          <p className="section-lead">{t("resfinder.genes.empty")}</p>
        ) : (
          <div className="table-wrap">
            <table className="consensus-table hit-detail-table">
              <thead>
                <tr>
                  <th>{t("table.gene")}</th>
                  <th>{t("table.identity")}</th>
                  <th>{t("table.coverage")}</th>
                  <th>{t("table.accession")}</th>
                  <th>{t("table.contig")}</th>
                  <th>{t("table.filter")}</th>
                </tr>
              </thead>
              <tbody>
                {contigGroups.map(([contig, hits]) =>
                  hits.map((hit, i) => {
                    const ok = passesFilter(hit, idMin, covMin);
                    return (
                      <tr key={`${contig}-${hit.gene_symbol}-${i}`}>
                        <td>
                          <strong>{plain(hit.gene_symbol)}</strong>
                          {i > 0 && (
                            <div className="muted">
                              {t("resfinder.altAllele")}
                            </div>
                          )}
                        </td>
                        <td>{pct(hit.sequence_identity)}</td>
                        <td>{pct(hit.coverage_percentage)}</td>
                        <td className="mono">
                          {plain(hit.reference_accession)}
                        </td>
                        <td className="mono">{contig}</td>
                        <td>
                          <span
                            className={`status-chip ${ok ? "susceptible" : "ambiguous"}`}
                          >
                            {ok ? t("table.pass") : t("table.fail")}
                          </span>
                        </td>
                      </tr>
                    );
                  }),
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <PointFinderSection
        status={report.extras?.pointfinder_status}
        species={report.extras?.pointfinder_species}
        reason={report.extras?.pointfinder_reason}
        mutations={(report.extras?.point_mutations ?? []) as PointMutationRow[]}
      />

      <section className="panel report-block">
        <h2 className="section-title report-section-title">
          {t("resfinder.pheno.title")}
        </h2>
        <p className="section-lead">{t("resfinder.pheno.lead")}</p>

        {phenotypes.length === 0 ? (
          <p className="section-lead">{t("resfinder.pheno.empty")}</p>
        ) : (
          <>
            <label className="report-toggle">
              <input
                type="checkbox"
                checked={showAllAgents}
                onChange={(e) => setShowAllAgents(e.target.checked)}
              />
              {t("resfinder.pheno.toggle", { count: phenotypes.length })}
            </label>

            <div className="table-wrap">
              <table className="consensus-table hit-detail-table">
                <thead>
                  <tr>
                    <th>{t("resfinder.col.antimicrobial")}</th>
                    <th>{t("resfinder.col.class")}</th>
                    <th>{t("resfinder.col.phenotype")}</th>
                    <th>{t("resfinder.col.match")}</th>
                    <th>{t("resfinder.col.background")}</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.length === 0 ? (
                    <tr>
                      <td colSpan={5}>{t("resfinder.pheno.none")}</td>
                    </tr>
                  ) : (
                    visibleRows.map((row, i) => (
                      <tr key={`${row.antimicrobial}-${i}`}>
                        <td>
                          <strong>{plain(row.antimicrobial)}</strong>
                        </td>
                        <td>{plain(row.drug_class)}</td>
                        <td>{plain(row.phenotype)}</td>
                        <td>{plain(row.match)}</td>
                        <td className="mono">
                          {plain(row.genetic_background)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <ul className="report-legend">
              {MATCH_LEGEND_KEYS.map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
