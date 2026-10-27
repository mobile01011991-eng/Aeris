import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  I18nContext,
  type I18nValue,
  type TranslationVars,
} from "./I18nContext";
import {
  LOCALES,
  TRANSLATIONS,
  type Lang,
  type TranslationKey,
} from "./translations";

const STORAGE_KEY = "aeris:lang";

function initialLang(): Lang {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "th") return stored;
  return navigator.language?.toLowerCase().startsWith("th") ? "th" : "en";
}

function interpolate(text: string, vars?: TranslationVars): string {
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  );
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    localStorage.setItem(STORAGE_KEY, next);
    setLangState(next);
  }, []);

  const t = useCallback(
    (key: TranslationKey, vars?: TranslationVars) => {
      const text = TRANSLATIONS[lang][key] ?? TRANSLATIONS.en[key] ?? key;
      return interpolate(text, vars);
    },
    [lang],
  );

  const value = useMemo<I18nValue>(
    () => ({ lang, setLang, t, locale: LOCALES[lang] }),
    [lang, setLang, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
