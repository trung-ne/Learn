import { describe, expect, it } from "vitest";
import { getSpeakingLanguages, speakingSnapshot } from "@/content/speaking-catalog";
import { speakingHref } from "@/lib/routes";
import { generateStaticParams } from "./page";

describe("static speaking routes", () => {
  it("generates only languages with supplied protocol inventories", () => {
    const params = generateStaticParams();
    const languages = getSpeakingLanguages();

    expect(params).toEqual(languages.map((language) => ({ language })));
    expect(params.map((item) => speakingHref(item.language))).toEqual(languages.map(speakingHref));
    expect(speakingSnapshot.protocols.every((protocol) => languages.includes(protocol.language))).toBe(true);
  });
});
