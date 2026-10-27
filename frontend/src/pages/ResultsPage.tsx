import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listResults } from "../api/client";
import { useI18n } from "../i18n/I18nContext";
import type { ResultSummary } from "../api/types";

export function ResultsPage() {
  const [history, setHistory] = useState<ResultSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { t, locale } = useI18n();

  useEffect(() => {
    let alive = true;
    listResults()
      .then((data) => {
        if (alive) setHistory(data);
      })
      .catch((err) => {
        if (alive) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section className="section">
      <h1 className="section-title">{t("samples.title")}</h1>
      <p className="section-lead">{t("samples.lead")}</p>

      <div className="panel">
        <div className="actions" style={{ marginTop: 0 }}>
          <Link className="btn btn-primary" to="/?demo=1">
            {t("samples.runDemo")}
          </Link>
          <Link className="btn btn-ghost" to="/">
            {t("samples.upload")}
          </Link>
        </div>

        <h2
          className="section-title"
          style={{ fontSize: "1.3rem", marginTop: "1.5rem" }}
        >
          {t("samples.recent")}
        </h2>

        {error && <div className="error-banner">{error}</div>}

        <div className="history-list">
          {history.length === 0 ? (
            <p className="section-lead">{t("samples.empty")}</p>
          ) : (
            history.map((h) => (
              <Link
                key={h.id}
                className="history-item"
                to={`/results/${encodeURIComponent(h.sample_id)}`}
              >
                <span>
                  <strong>{h.sample_id}</strong>
                  <div className="muted">
                    {h.processed_at
                      ? new Date(h.processed_at).toLocaleString(locale)
                      : "—"}
                  </div>
                </span>
                <span className="muted">{t("samples.open")}</span>
              </Link>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
