'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils/cn';

interface StreamingMarkdownProps {
  content: string;
  className?: string;
}

/**
 * Wrapper de ReactMarkdown com remark-gfm + classes Tailwind.
 *
 * Renderiza markdown progressivo durante o streaming. Hoje a UI
 * mostra a `content` completa do FinalAnswer quando chega — partial
 * markdown via eventos SSE intermediarios e uso futuro.
 */
export function StreamingMarkdown({ content, className }: StreamingMarkdownProps) {
  return (
    <div
      className={cn(
        'prose-body max-w-none text-sm leading-relaxed text-foreground',
        '[&>h1]:mb-3 [&>h1]:mt-4 [&>h1]:text-xl [&>h1]:font-semibold',
        '[&>h2]:mb-2 [&>h2]:mt-4 [&>h2]:text-lg [&>h2]:font-semibold',
        '[&>h3]:mb-2 [&>h3]:mt-3 [&>h3]:text-base [&>h3]:font-semibold',
        '[&>p]:mb-3',
        '[&>ul]:mb-3 [&>ul]:list-disc [&>ul]:pl-5',
        '[&>ol]:mb-3 [&>ol]:list-decimal [&>ol]:pl-5',
        '[&>blockquote]:border-l-2 [&>blockquote]:border-primary [&>blockquote]:pl-3 [&>blockquote]:italic [&>blockquote]:text-muted-foreground',
        '[&>hr]:my-4 [&>hr]:border-border',
        '[&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs',
        '[&_a]:text-primary [&_a]:underline',
        '[&_table]:my-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs',
        '[&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left',
        '[&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1',
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
