export function normalizeAnswer(value: string): string {
  return value.normalize("NFC").trim().replace(/\s+/gu, " ").toLocaleLowerCase();
}

export function matchesAnyAnswer(value: string, answers: readonly string[]): boolean {
  const normalized = normalizeAnswer(value);
  return answers.some((answer) => normalizeAnswer(answer) === normalized);
}

export function arraysMatch(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((item, index) => normalizeAnswer(item) === normalizeAnswer(right[index] ?? ""));
}
