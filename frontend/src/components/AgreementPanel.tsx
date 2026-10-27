import { useMemo } from "react";
import { geneFamily, passesFilter, stripGenePrefix, type ToolView } from "../api/reports";
import { useI18n } from "../i18n/I18nContext";

interface FamilyRow {
  family: string;
  tools: string[];
  genes: string[];
}

/**
 * Optional cross-check: which gene families the four database tools agree on.
 *
 * Gene-family level, database tools only — DeepARG is never in the denominator.
 */
export function AgreementPanel({
  views,
  idMin,
  covMin,
}: {
  views: ToolView[];
  idMin: number;
  covMin: number;
}) {
  const { t } = useI18n();
  const databaseViews = views.filter((v) => v.kind !== "ai");

  const rows = useMemo<FamilyRow[]>(() => {
    const families = new Map<string, { tools: Set<string>; genes: Set<string> }>();

    views
      .filter((v) => v.kind !== "ai" && v.report?.success)
      .forEach((view) => {
        view.report?.hits
          .filter((hit) => passesFilter(hit, idMin, covMin))
          .forEach((hit) => {
            const family = geneFamily(hit.gene_symbol);
            if (!family) return;
            const entry =
              families.get(family) ?? { tools: new Set(), genes: new Set() };
            entry.tools.add(view.label);
            const gene = stripGenePrefix(hit.gene_symbol);
            if (gene) entry.genes.add(gene);
            families.set(family, entry);
          });
      });

    return [...families.entries()]
      .map(([family, entry]) => ({
        family,
        tools: [...entry.tools].sort(),
        genes: [...entry.genes].sort(),
      }))
      .sort(
        (a, b) => b.tools.length - a.tools.length || a.family.localeCompare(b.family),
      );
  }, [views, idMin, covMin]);

  if (!rows.length) return null;

  return (
    <details className="panel agreement-panel">
      <summary>{t("agreement.summary", { count: rows.length })}</summary>
      <p className="section-lead agreement-lead">
        {t("agreement.lead", { total: databaseViews.length })}
      </p>

      <div className="table-wrap">
        <table className="consensus-table">
          <thead>
            <tr>
              <th>{t("agreement.col.family")}</th>
              <th>{t("agreement.col.seenBy")}</th>
              <th>{t("agreement.col.tools")}</th>
              <th>{t("agreement.col.genes")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.family}>
                <td>
                  <strong>{row.family}</strong>
                </td>
                <td className="mono">
                  {t("agreement.seenBy", {
                    n: row.tools.length,
                    total: databaseViews.length,
                  })}
                </td>
                <td>
                  <div className="tool-list">
                    {row.tools.map((tool) => (
                      <span className="tag" key={tool}>
                        {tool}
                      </span>
                    ))}
                  </div>
                </td>
                <td>
                  <div className="gene-list">
                    {row.genes.map((gene) => (
                      <span className="tag" key={gene}>
                        {gene}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
