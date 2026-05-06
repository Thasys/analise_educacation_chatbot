import { beforeEach, describe, expect, it } from 'vitest';
import { useChatStore } from '@/lib/stores/chatStore';
import type { FinalAnswer } from '@/types/domain';

const FAKE_FINAL: FinalAnswer = {
  markdown: '# Resposta\n\nCorpo.',
  profile_used: 'researcher',
  flow_used: 'data',
  sources_cited: ['worldbank'],
  visualizations: [],
  citations: [],
  warnings: [],
  follow_up_suggestions: [],
};

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.getState().clear();
  });

  it('pushes user message and returns id', () => {
    const id = useChatStore.getState().pushUserMessage('Pergunta?');
    expect(id).toMatch(/^msg_/);
    const messages = useChatStore.getState().messages;
    expect(messages).toHaveLength(1);
    const first = messages[0];
    expect(first?.role).toBe('user');
    expect(first?.content).toBe('Pergunta?');
  });

  it('starts assistant message and tracks current id', () => {
    useChatStore.getState().pushUserMessage('q');
    useChatStore.getState().startAssistantMessage('asst_1');
    expect(useChatStore.getState().currentAssistantId).toBe('asst_1');
    expect(useChatStore.getState().messages).toHaveLength(2);
  });

  it('appends events and markdown chunks', () => {
    useChatStore.getState().startAssistantMessage('a1');
    useChatStore.getState().appendEvent('a1', {
      type: 'agent_started',
      agent: 'Orchestrator',
      ts: 1,
    });
    useChatStore.getState().appendMarkdownChunk('a1', '# Olá');
    useChatStore.getState().appendMarkdownChunk('a1', ' mundo');
    const msg = useChatStore.getState().messages.find((m) => m.id === 'a1');
    expect(msg?.events).toHaveLength(1);
    expect(msg?.content).toBe('# Olá mundo');
  });

  it('finalizes assistant message with FinalAnswer', () => {
    useChatStore.getState().startAssistantMessage('a1');
    useChatStore.getState().finalizeAssistantMessage('a1', FAKE_FINAL);
    const msg = useChatStore.getState().messages.find((m) => m.id === 'a1');
    expect(msg?.final).toEqual(FAKE_FINAL);
    expect(msg?.content).toBe(FAKE_FINAL.markdown);
    expect(useChatStore.getState().currentAssistantId).toBeNull();
  });
});
