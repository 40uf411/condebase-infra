import en from "./dictionaries/en";
import es from "./dictionaries/es";
import fr from "./dictionaries/fr";

export const DEFAULT_LANGUAGE = "en";
export const SUPPORTED_LANGUAGES = ["en", "es", "fr"];
export const LANGUAGE_LABEL_KEYS = {
  en: "languageEnglish",
  es: "languageSpanish",
  fr: "languageFrench",
};

const dictionaries = {
  en,
  es,
  fr,
};

export function normalizeLanguage(value) {
  if (typeof value !== "string") {
    return DEFAULT_LANGUAGE;
  }

  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return DEFAULT_LANGUAGE;
  }
  if (SUPPORTED_LANGUAGES.includes(normalized)) {
    return normalized;
  }

  const prefix = normalized.split("-", 1)[0];
  if (SUPPORTED_LANGUAGES.includes(prefix)) {
    return prefix;
  }

  return DEFAULT_LANGUAGE;
}

export function getDictionary(language) {
  return dictionaries[normalizeLanguage(language)] || dictionaries[DEFAULT_LANGUAGE];
}

export function translate(dictionary, key, params = {}) {
  const template = dictionary[key] ?? dictionaries[DEFAULT_LANGUAGE][key] ?? key;
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, capture) => {
    if (params[capture] === undefined || params[capture] === null) {
      return match;
    }
    return String(params[capture]);
  });
}
