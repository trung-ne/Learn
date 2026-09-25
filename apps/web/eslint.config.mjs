import js from "@eslint/js";
import nextVitals from "eslint-config-next/core-web-vitals";

export default [
  js.configs.recommended,
  ...nextVitals,
  {
    ignores: [".next/**", "out/**", "coverage/**", "src/content/generated/**"],
  },
];
