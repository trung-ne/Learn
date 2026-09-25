export const languages = {
  en: {
    code: "en",
    name: "English",
    nativeName: "English",
    availableLevels: ["A1", "A2", "B1", "B2", "C1", "C2"],
  },
  de: {
    code: "de",
    name: "German",
    nativeName: "Deutsch",
    availableLevels: ["A1"],
  },
} as const;

export type LanguageCode = keyof typeof languages;
export type CourseLevel = (typeof languages)[LanguageCode]["availableLevels"][number];

export function isLanguageCode(value: string): value is LanguageCode {
  return Object.hasOwn(languages, value);
}

export function getLanguageConfiguration(code: string) {
  return isLanguageCode(code) ? languages[code] : undefined;
}

export function isAvailableLevel(language: LanguageCode, level: string): level is CourseLevel {
  return (languages[language].availableLevels as readonly string[]).includes(level);
}
