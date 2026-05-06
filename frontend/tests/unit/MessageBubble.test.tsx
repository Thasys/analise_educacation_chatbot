import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageBubble } from '@/components/chat/MessageBubble';
import type { ChatMessage } from '@/lib/stores/chatStore';
import type { FinalAnswer } from '@/types/domain';

const FINAL_ANSWER: FinalAnswer = {
  markdown: '# Título\n\nCorpo da resposta com **negrito**.',
  profile_used: 'researcher',
  flow_used: 'data',
  sources_cited: ['worldbank', 'unesco'],
  visualizations: [],
  citations: [],
  warnings: ['Cobertura limitada para 2024.'],
  follow_up_suggestions: ['Pergunta extra 1', 'Pergunta extra 2'],
};

describe('MessageBubble', () => {
  it('renders user message with content', () => {
    const message: ChatMessage = {
      id: 'u1',
      role: 'user',
      content: 'Como BR vs FIN em gasto?',
      events: [],
      ts: 1,
    };
    render(<MessageBubble message={message} />);
    expect(screen.getByText('Como BR vs FIN em gasto?')).toBeInTheDocument();
  });

  it('renders assistant message with final markdown', () => {
    const message: ChatMessage = {
      id: 'a1',
      role: 'assistant',
      content: FINAL_ANSWER.markdown,
      events: [],
      final: FINAL_ANSWER,
      ts: 1,
    };
    render(<MessageBubble message={message} />);
    expect(screen.getByText('Título')).toBeInTheDocument();
    expect(screen.getByText(/Corpo da resposta/)).toBeInTheDocument();
    // Footer com fontes
    expect(screen.getByText(/worldbank, unesco/)).toBeInTheDocument();
    // Warnings
    expect(screen.getByText(/Cobertura limitada/)).toBeInTheDocument();
    // Follow-ups
    expect(screen.getByText('→ Pergunta extra 1')).toBeInTheDocument();
  });

  it('shows "Processando…" when assistant is streaming with no content', () => {
    const message: ChatMessage = {
      id: 'a1',
      role: 'assistant',
      content: '',
      events: [{ type: 'agent_started', agent: 'Core', ts: 1 }],
      ts: 1,
    };
    render(<MessageBubble message={message} isStreaming={true} />);
    expect(screen.getByText('Processando…')).toBeInTheDocument();
  });

  it('shows error banner when error event present', () => {
    const message: ChatMessage = {
      id: 'a1',
      role: 'assistant',
      content: '',
      events: [{ type: 'error', error: 'simulated failure', ts: 1 }],
      ts: 1,
    };
    render(<MessageBubble message={message} />);
    expect(screen.getByText('Falha durante a execução')).toBeInTheDocument();
    expect(screen.getByText('simulated failure')).toBeInTheDocument();
  });
});
