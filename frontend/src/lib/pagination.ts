export const CLIENT_PAGE_SIZE = 12;


export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};


export function getTotalPages(
  count: number,
  pageSize = CLIENT_PAGE_SIZE
) {
  return Math.max(
    Math.ceil(
      count / pageSize
    ),
    1
  );
}


export function normalizePage(
  value: string | null
) {
  const page = Number(
    value
  );

  if (
    Number.isInteger(page) &&
    page > 0
  ) {
    return page;
  }

  return 1;
}
