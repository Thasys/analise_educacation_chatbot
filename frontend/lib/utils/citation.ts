import type { Citation } from '@/types/domain';

/**
 * Formata os autores de uma citacao em string curta.
 *
 * Regra: 0 -> "Autor(es) nao informado(s)"
 *        1 -> "Smith"
 *        2 -> "Smith & Jones"
 *        3+ -> "Smith et al."
 */
export function formatAuthors(authors: string[]): string {
  if (authors.length === 0) return 'Autor(es) não informado(s)';
  if (authors.length === 1) return authors[0] ?? '';
  if (authors.length === 2) return `${authors[0]} & ${authors[1]}`;
  return `${authors[0]} et al.`;
}

/**
 * Formata a meta-informacao de uma citacao (autores + ano + jornal).
 *
 * - `mode: 'full'` -> "Smith & Jones (2021). Journal of X"
 * - `mode: 'short'` -> "Smith et al. (2021)"
 *
 * Centraliza a formatacao que estava duplicada entre `CitationCard`
 * (variante full) e `ContextPanel` (variante short) (DRY #9.3).
 */
export function formatCitationMeta(
  citation: Citation,
  options: { mode: 'full' | 'short' } = { mode: 'full' },
): string {
  const authors = formatAuthors(citation.authors);
  const year = citation.year ? ` (${citation.year})` : '';
  if (options.mode === 'short') {
    return `${authors}${year}`.trim();
  }
  const journal = citation.journal ? `. ${citation.journal}` : '';
  return `${authors}${year}${journal}`.trim();
}
