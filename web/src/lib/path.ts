/** First path segment after `/p/` is the project slug (web-change-reader D3).
 *  Nested routes such as `/p/:slug/c/:change` must not leak into the slug. */
export function projectSlugFromPath(pathname: string): string | null {
  const match = /^\/p\/([^/]+)/.exec(pathname);
  return match ? match[1] : null;
}
