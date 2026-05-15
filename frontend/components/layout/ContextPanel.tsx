'use client';

import { useChatStore } from '@/lib/stores/chatStore';
import { useProfileStore } from '@/lib/stores/profileStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sparkles } from 'lucide-react';
import { DoiLink } from '@/components/citations/DoiLink';
import { formatCitationMeta } from '@/lib/utils/citation';

export function ContextPanel() {
  const messages = useChatStore((s) => s.messages);
  const profile = useProfileStore((s) => s.profile);
  const lastFinal = [...messages].reverse().find((m) => m.role === 'assistant' && m.final)?.final;

  return (
    <aside className="flex h-full w-[320px] flex-col gap-4 overflow-y-auto border-l border-border bg-card/30 p-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-primary" aria-hidden />
            Sessão
          </CardTitle>
          <CardDescription className="text-xs">
            Perfil detectado: <span className="font-medium text-foreground">{profile}</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-1 pt-0 text-xs text-muted-foreground">
          <div>{messages.length} mensagens</div>
          {lastFinal ? (
            <div>
              Fluxo: <span className="font-mono">{lastFinal.flow_used}</span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {lastFinal && lastFinal.sources_cited.length > 0 ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Fontes</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ul className="space-y-1 text-xs">
              {lastFinal.sources_cited.map((s) => (
                <li key={s} className="font-mono text-muted-foreground">
                  · {s}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {lastFinal && lastFinal.citations.length > 0 ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Citações ({lastFinal.citations.length})</CardTitle>
            <CardDescription className="text-xs">
              DOIs validados pelo Citation Agent.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {lastFinal.citations.map((c, i) => (
              <div key={c.doi ?? `${c.title}-${i}`} className="border-l-2 border-primary/40 pl-2">
                <p className="text-xs font-medium leading-snug text-foreground">{c.title}</p>
                <p className="text-[11px] text-muted-foreground">
                  {formatCitationMeta(c, { mode: 'short' })}
                </p>
                {c.doi ? <DoiLink doi={c.doi} variant="text" /> : null}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {!lastFinal ? (
        <p className="px-1 text-xs text-muted-foreground">
          Faça uma pergunta para popular as fontes e citações desta sessão.
        </p>
      ) : null}
    </aside>
  );
}
