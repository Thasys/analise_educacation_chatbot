import { ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils/cn';

interface DoiLinkProps {
  doi: string;
  /**
   * 'icon' — botao quadrado pequeno (CitationCard).
   * 'text' — link textual `doi.org/10.xxx/...` (ContextPanel).
   */
  variant?: 'icon' | 'text';
  className?: string;
}

/**
 * Link clicavel para um DOI.
 *
 * Centraliza `target="_blank" rel="noopener noreferrer"`, o prefixo
 * `https://doi.org/`, e a logica de label/title — antes duplicada entre
 * `CitationCard` e `ContextPanel` (DRY #9.2).
 *
 * Confia no formato do DOI ja validado pelo Citation Agent
 * (CiteResolveTool aplica regex `^10\.\d{4,9}/...`). Para inputs sem
 * validacao previa, valide antes ou aceite link "quebrado".
 */
export function DoiLink({ doi, variant = 'text', className }: DoiLinkProps) {
  const href = `https://doi.org/${doi}`;
  if (variant === 'icon') {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          'shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground',
          className,
        )}
        aria-label={`Abrir DOI ${doi} em nova aba`}
        title={`doi.org/${doi}`}
      >
        <ExternalLink className="h-3.5 w-3.5" aria-hidden />
      </a>
    );
  }
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn('font-mono text-[10px] text-primary hover:underline', className)}
    >
      doi.org/{doi}
    </a>
  );
}
