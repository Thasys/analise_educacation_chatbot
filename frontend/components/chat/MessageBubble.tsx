'use client';

import { AlertCircle, User } from 'lucide-react';
import type { ChatMessage } from '@/lib/stores/chatStore';
import { cn } from '@/lib/utils/cn';
import { AgentReasoning } from '@/components/chat/AgentReasoning';
import { StreamingMarkdown } from '@/components/chat/StreamingMarkdown';
import { InlineChart } from '@/components/charts/InlineChart';
import { ChartErrorBoundary } from '@/components/charts/ChartErrorBoundary';
import { CitationPanel } from '@/components/citations/CitationPanel';

interface MessageBubbleProps {
  message: ChatMessage;
  /** True se este eh o assistant message atualmente em streaming. */
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className="flex items-start gap-3 px-2 py-1.5">
        <div className="mt-0.5 rounded-full bg-muted p-1.5">
          <User className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        </div>
        <p className="flex-1 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {message.content}
        </p>
      </div>
    );
  }

  // assistant
  const errorEvent = message.events.find((e) => e.type === 'error');
  const hasContent = message.content.length > 0 || message.final !== undefined;

  return (
    <article
      className={cn(
        'space-y-3 rounded-md border border-border bg-card/30 p-4',
        isStreaming && 'animate-pulse-subtle',
      )}
    >
      <AgentReasoning events={message.events} loading={isStreaming} />

      {errorEvent ? (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">Falha durante a execução</p>
            <p className="font-mono text-xs">
              {errorEvent.type === 'error' ? errorEvent.error : ''}
            </p>
          </div>
        </div>
      ) : null}

      {hasContent ? (
        <StreamingMarkdown content={message.content || message.final?.markdown || ''} />
      ) : isStreaming ? (
        <p className="text-xs text-muted-foreground">Processando…</p>
      ) : null}

      {message.final && message.final.visualizations.length > 0 ? (
        <div className="space-y-3">
          {message.final.visualizations.map((spec, i) => (
            <ChartErrorBoundary key={i}>
              <InlineChart spec={spec} />
            </ChartErrorBoundary>
          ))}
        </div>
      ) : null}

      {message.final && message.final.citations.length > 0 ? (
        <CitationPanel citations={message.final.citations} />
      ) : null}

      {message.final ? (
        <FinalAnswerFooter
          sources={message.final.sources_cited}
          warnings={message.final.warnings}
          followUps={message.final.follow_up_suggestions}
        />
      ) : null}
    </article>
  );
}

function FinalAnswerFooter({
  sources,
  warnings,
  followUps,
}: {
  sources: string[];
  warnings: string[];
  followUps: string[];
}) {
  if (sources.length === 0 && warnings.length === 0 && followUps.length === 0) return null;
  return (
    <footer className="space-y-2 border-t border-border pt-3 text-xs">
      {sources.length > 0 ? (
        <div>
          <span className="font-mono uppercase tracking-wide text-muted-foreground">Fontes: </span>
          <span className="text-foreground">{sources.join(', ')}</span>
        </div>
      ) : null}
      {warnings.length > 0 ? (
        <ul className="space-y-0.5 text-amber-400">
          {warnings.map((w, i) => (
            <li key={i}>⚠ {w}</li>
          ))}
        </ul>
      ) : null}
      {followUps.length > 0 ? (
        <div>
          <p className="mb-1 font-mono uppercase tracking-wide text-muted-foreground">
            Para aprofundar
          </p>
          <ul className="space-y-1">
            {followUps.map((f, i) => (
              <li key={i} className="text-muted-foreground">
                → {f}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </footer>
  );
}
