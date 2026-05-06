'use client';

import { useState } from 'react';
import * as Collapsible from '@radix-ui/react-collapsible';
import { ChevronRight, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils/cn';
import type { StreamEvent } from '@/types/domain';

interface AgentReasoningProps {
  events: StreamEvent[];
  loading: boolean;
}

interface AgentTimelineEntry {
  agent: string;
  status: 'started' | 'done' | 'error';
  startedAt: number;
  doneAt?: number;
  meta?: string;
}

function buildTimeline(events: StreamEvent[]): AgentTimelineEntry[] {
  const map = new Map<string, AgentTimelineEntry>();
  for (const event of events) {
    if (event.type === 'agent_started') {
      map.set(event.agent, {
        agent: event.agent,
        status: 'started',
        startedAt: event.ts,
      });
    } else if (event.type === 'agent_done') {
      const existing = map.get(event.agent);
      const meta = formatMeta(event);
      const entry = existing ?? {
        agent: event.agent,
        status: 'done' as const,
        startedAt: event.ts,
      };
      const updated: AgentTimelineEntry = {
        ...entry,
        status: 'done',
        doneAt: event.ts,
      };
      if (meta !== undefined) {
        updated.meta = meta;
      }
      map.set(event.agent, updated);
    } else if (event.type === 'error') {
      const last = Array.from(map.values()).at(-1);
      if (last) {
        map.set(last.agent, { ...last, status: 'error', doneAt: event.ts });
      }
    }
  }
  return Array.from(map.values());
}

function formatMeta(event: Extract<StreamEvent, { type: 'agent_done' }>): string | undefined {
  const parts: string[] = [];
  if (event.tool_calls !== undefined) parts.push(`${event.tool_calls} tool call(s)`);
  if (event.method) parts.push(`method=${event.method}`);
  if (event.sample_size !== undefined) parts.push(`N=${event.sample_size}`);
  if (event.items !== undefined) parts.push(`${event.items} item(s)`);
  if (event.chart_type) parts.push(`chart=${event.chart_type}`);
  if (event.result?.flow) parts.push(`flow=${String(event.result.flow)}`);
  if (event.result?.profile) parts.push(`profile=${String(event.result.profile)}`);
  return parts.length > 0 ? parts.join(' · ') : undefined;
}

function StatusIcon({ status }: { status: AgentTimelineEntry['status'] }) {
  if (status === 'done') {
    return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" aria-label="concluído" />;
  }
  if (status === 'error') {
    return <AlertCircle className="h-3.5 w-3.5 text-destructive" aria-label="erro" />;
  }
  return <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" aria-label="rodando" />;
}

export function AgentReasoning({ events, loading }: AgentReasoningProps) {
  const [open, setOpen] = useState(true);
  const timeline = buildTimeline(events);
  if (timeline.length === 0 && !loading) return null;

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="rounded-md border border-border bg-card/40">
      <Collapsible.Trigger className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-muted-foreground hover:text-foreground">
        <ChevronRight
          className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-90')}
          aria-hidden
        />
        <span className="font-mono uppercase tracking-wide">
          Reasoning ({timeline.length} {timeline.length === 1 ? 'etapa' : 'etapas'})
        </span>
      </Collapsible.Trigger>
      <Collapsible.Content className="px-3 pb-3">
        <ol className="space-y-1.5 text-xs">
          {timeline.map((entry, idx) => (
            <li key={`${entry.agent}-${idx}`} className="flex items-start gap-2">
              <span className="mt-0.5">
                <StatusIcon status={entry.status} />
              </span>
              <div className="flex flex-col">
                <span className="font-medium text-foreground">{entry.agent}</span>
                {entry.meta ? (
                  <span className="font-mono text-[11px] text-muted-foreground">{entry.meta}</span>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
