'use client';

import { useCallback, useState } from 'react';
import { useChatStore } from '@/lib/stores/chatStore';
import { useProfileStore } from '@/lib/stores/profileStore';
import { streamChat } from '@/lib/streaming';
import type { ProfileKind, StreamEvent } from '@/types/domain';

const PROFILES: ProfileKind[] = ['researcher', 'policy', 'student'];

function isProfileKind(value: unknown): value is ProfileKind {
  return typeof value === 'string' && (PROFILES as readonly string[]).includes(value);
}

export interface UseChatReturn {
  /** True enquanto streamChat esta em curso. */
  loading: boolean;
  /** Mensagem de erro do ultimo envio (se houver). */
  error: string | null;
  /** Envia uma pergunta. Cria mensagens user + assistant no store, drena SSE, finaliza. */
  send: (question: string) => Promise<void>;
}

/**
 * Hook que orquestra streamChat + chatStore + profileStore.
 *
 * Fluxo de uma chamada `send(q)`:
 *   1. push user message no chatStore
 *   2. start assistant message com id gerado
 *   3. abre stream via streamChat
 *   4. para cada evento: appendEvent + (opcional) appendMarkdownChunk
 *   5. ao detectar agent_done da Core, atualiza profileStore (auto-detect)
 *   6. final_answer -> finalizeAssistantMessage
 *   7. error -> seta state error e marca assistant message com warning
 */
export function useChat(): UseChatReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pushUserMessage = useChatStore((s) => s.pushUserMessage);
  const startAssistantMessage = useChatStore((s) => s.startAssistantMessage);
  const appendEvent = useChatStore((s) => s.appendEvent);
  const finalizeAssistantMessage = useChatStore((s) => s.finalizeAssistantMessage);
  const setProfile = useProfileStore((s) => s.setProfile);

  const send = useCallback(
    async (question: string): Promise<void> => {
      const trimmed = question.trim();
      if (!trimmed) return;
      setError(null);
      setLoading(true);

      pushUserMessage(trimmed);
      const assistantId = `asst_${Date.now()}`;
      startAssistantMessage(assistantId);

      const onEvent = (event: StreamEvent): void => {
        appendEvent(assistantId, event);
        // Auto-deteccao de perfil via output da Core Crew
        if (event.type === 'agent_done' && event.agent.startsWith('Core')) {
          const detected = event.result?.profile;
          if (isProfileKind(detected)) {
            setProfile(detected);
          }
        }
      };

      try {
        const final = await streamChat(trimmed, {
          onEvent,
          onFinal: (f) => finalizeAssistantMessage(assistantId, f),
        });
        // Sanity: se o servidor mandou final_answer e onFinal nao foi
        // chamado por algum motivo, garantir finalizacao.
        const state = useChatStore.getState();
        if (state.currentAssistantId === assistantId) {
          finalizeAssistantMessage(assistantId, final);
        }
      } catch (exc) {
        const message = exc instanceof Error ? exc.message : String(exc);
        setError(message);
        appendEvent(assistantId, {
          type: 'error',
          error: message,
          ts: Date.now() / 1000,
        });
      } finally {
        setLoading(false);
      }
    },
    [appendEvent, finalizeAssistantMessage, pushUserMessage, setProfile, startAssistantMessage],
  );

  return { loading, error, send };
}
