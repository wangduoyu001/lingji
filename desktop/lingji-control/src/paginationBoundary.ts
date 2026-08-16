export type PaginationBoundary = {
  has_more?: boolean | null;
  total?: number | null;
};

export function canLoadNextPage({
  pagination,
  offset,
  limit,
}: {
  pagination?: PaginationBoundary | null;
  offset: number;
  limit: number;
}): boolean {
  if (pagination?.has_more === true) return true;
  if (pagination?.has_more === false) return false;
  const total = pagination?.total;
  if (typeof total === "number" && Number.isFinite(total) && total >= 0) {
    return offset + limit < total;
  }
  // Unknown is not evidence that another page exists. A full page by itself must not
  // create a "next" action because that recreates the old infinite-pagination bug.
  return false;
}
