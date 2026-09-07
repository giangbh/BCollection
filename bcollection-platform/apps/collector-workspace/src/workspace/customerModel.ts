import type { Scope } from "./types";

/** Arrears component vs remainder, NOT delinquent-loan vs current-loan balances. */
export function debtComposition(scope: Scope) {
  const { total_vnd: total, overdue_vnd: overdue } = scope;
  if (
    !scope.exposures.length ||
    scope.conflict_count ||
    scope.verified_count !== scope.exposures.length ||
    total == null ||
    overdue == null ||
    !Number.isSafeInteger(total) ||
    !Number.isSafeInteger(overdue) ||
    total < 0 ||
    overdue < 0 ||
    overdue > total
  )
    return null;
  return {
    total,
    overdue,
    remainder: total - overdue,
    overduePercent: total ? (overdue / total) * 100 : 0,
  };
}

export function normalizedSearch(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLocaleLowerCase("vi")
    .trim();
}
