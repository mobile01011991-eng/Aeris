import { createContext, useContext } from "react";
import type { Lang, TranslationKey } from "./translations";

export type TranslationVars = Record<string, string | number>;

export interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  /** Translate a key, filling `{name}` placeholders. Falls back to English. */
  t: (key: TranslationKey, vars?: TranslationVars) => string;
  /** Locale for `toLocaleString` calls. */
  locale: string;
}

export const I18nContext = createContext<I18nValue | null>(null);

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return value;
}
