'use client';

import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useChat } from '@/lib/hooks/useChat';
import { useChatStore } from '@/lib/stores/chatStore';
import { useProfileStore } from '@/lib/stores/profileStore';
import { InputBox } from '@/components/chat/InputBox';
import { MessageBubble } from '@/components/chat/MessageBubble';
import type { ProfileKind } from '@/types/domain';

const PROFILES: ProfileKind[] = ['researcher', 'policy', 'student'];
const PROFILE_LABEL: Record<ProfileKind, string> = {
  researcher: 'Pesquisador',
  policy: 'Gestor público',
  student: 'Estudante',
};

const PROFILE_HINT: Record<ProfileKind, string> = {
  researcher:
    'Tom técnico, fontes serif, z-scores e DOIs visíveis, sem emojis.',
  policy:
    'Foco em decisão e PNE meta 20, tons institucionais, números arredondados.',
  student:
    'Tom amigável, glossário inline, tipografia mais aberta, accent verde.',
};

const SAMPLE_QUESTIONS = [
  'Como o Brasil se compara com a Finlândia em gasto educacional em 2020?',
  'Onde o Brasil aparece em alfabetização entre países da América Latina?',
  'O que significa ISCED 2011 nível 2?',
];

export function Chat() {
  const profile = useProfileStore((s) => s.profile);
  const setProfile = useProfileStore((s) => s.setProfile);
  const messages = useChatStore((s) => s.messages);
  const currentAssistantId = useChatStore((s) => s.currentAssistantId);
  const { loading, error, send } = useChat();
  const [seed, setSeed] = useState('');

  const handleSubmit = (q: string): void => {
    setSeed('');
    void send(q);
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">Análise Educacional Comparada</h1>
          <p className="text-xs text-muted-foreground">
            Pergunte sobre educação básica BR × Internacional. Respostas com dados, citações e
            visualizações.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Perfil:</span>
          <div className="flex gap-1 rounded-md border border-border p-1">
            {PROFILES.map((p) => (
              <Button
                key={p}
                size="sm"
                variant={p === profile ? 'default' : 'ghost'}
                onClick={() => setProfile(p, true)}
                className="h-7 px-2 text-xs"
                title={PROFILE_HINT[p]}
              >
                {PROFILE_LABEL[p]}
              </Button>
            ))}
          </div>
        </div>
      </header>

      <div className="flex flex-1 flex-col overflow-y-auto p-6">
        {messages.length === 0 ? (
          <EmptyState onPick={(q) => setSeed(q)} />
        ) : (
          <ol className="mx-auto w-full max-w-2xl space-y-4">
            {messages.map((m) => (
              <li key={m.id}>
                <MessageBubble message={m} isStreaming={m.id === currentAssistantId} />
              </li>
            ))}
          </ol>
        )}

        {error ? (
          <div
            role="alert"
            className="mx-auto mt-4 max-w-2xl rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive"
          >
            {error}
          </div>
        ) : null}
      </div>

      <footer className="border-t border-border bg-card/30 p-4">
        <InputBox onSubmit={handleSubmit} disabled={loading} initialValue={seed} key={seed} />
        <p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-muted-foreground">
          Ctrl+Enter para enviar · LLM pode levar 20-60s para responder no fluxo data
        </p>
      </footer>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 self-center">
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
          <Sparkles className="h-8 w-8 text-primary" aria-hidden />
          <h2 className="text-lg font-semibold">Pronto para perguntar</h2>
          <p className="max-w-md text-sm text-muted-foreground">
            Sistema multi-agente CrewAI consulta os marts Gold em DuckDB e fundamenta respostas
            com referências DOI do RAG.
          </p>
        </CardContent>
      </Card>

      <div>
        <p className="mb-2 px-1 text-xs uppercase tracking-wide text-muted-foreground">
          Perguntas de exemplo
        </p>
        <ul className="space-y-2">
          {SAMPLE_QUESTIONS.map((q) => (
            <li key={q}>
              <button
                type="button"
                onClick={() => onPick(q)}
                className="w-full rounded-md border border-border bg-card/40 px-4 py-3 text-left text-sm transition-colors hover:bg-accent/40"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
