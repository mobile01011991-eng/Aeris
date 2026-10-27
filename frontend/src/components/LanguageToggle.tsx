import { useI18n } from "../i18n/I18nContext";
import { LANGUAGES } from "../i18n/translations";

export function LanguageToggle() {
  const { lang, setLang, t } = useI18n();

  return (
    <div className="lang-toggle" role="group" aria-label={t("lang.label")}>
      {LANGUAGES.map((option) => (
        <button
          key={option.code}
          type="button"
          className={option.code === lang ? "active" : ""}
          title={option.title}
          aria-pressed={option.code === lang}
          onClick={() => setLang(option.code)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
