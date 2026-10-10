import { describe, expect, it } from "vitest";
import { getPronunciationLanguages, pronunciationSnapshot } from "@/content/pronunciation-catalog";
import { pronunciationHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static pronunciation routes", () => {
  it("generates only languages with supplied protocol inventories", () => {
    const params = generateStaticParams();
    const languages = getPronunciationLanguages();

    expect(params).toEqual(languages.map((language) => ({ language })));
    expect(params.map((item) => pronunciationHref(item.language))).toEqual(languages.map(pronunciationHref));
    expect(pronunciationSnapshot.protocols.every((protocol) => languages.includes(protocol.language))).toBe(true);
  });
});
