import { useI18n } from "../i18n/I18nContext";

/** Idle ambient field — soft bacterial shapes drifting before analysis. */
export function BacteriaField() {
  const { t } = useI18n();

  return (
    <div className="bact-field" aria-hidden="true">
      <div className="bact-glow" />
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <span key={i} className={`bact b${i}`}>
          <span className="bact-body" />
          <span className="bact-flagella" />
        </span>
      ))}
      <div className="bact-caption">
        <strong>{t("idle.title")}</strong>
        <span>{t("idle.hint")}</span>
      </div>
    </div>
  );
}
