import { create } from 'zustand';
import type { FinalAnswer, StreamEvent } from '@/types/domain';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  /** Markdown ja parseado (resposta) ou texto puro (pergunta). */
  content: string;
  /** Eventos de streaming acumulados durante a resposta (reasoning trace). */
  events: StreamEvent[];
  /** FinalAnswer estruturado quando chega event="final_answer". */
  final?: FinalAnswer;
  ts: number;
}

interface ChatState {
  messages: ChatMessage[];
  /** Mensagem atualmente em streaming (assistant), se houver. */
  currentAssistantId: string | null;
  pushUserMessage: (content: string) => string;
  startAssistantMessage: (id: string) => void;
  appendEvent: (id: string, event: StreamEvent) => void;
  appendMarkdownChunk: (id: string, chunk: string) => void;
  finalizeAssistantMessage: (id: string, final: FinalAnswer) => void;
  clear: () => void;
}

let nextId = 0;
const genId = (): string => `msg_${Date.now()}_${nextId++}`;

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  currentAssistantId: null,

  pushUserMessage: (content) => {
    const id = genId();
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: 'user', content, events: [], ts: Date.now() },
      ],
    }));
    return id;
  },

  startAssistantMessage: (id) =>
    set((state) => ({
      currentAssistantId: id,
      messages: [
        ...state.messages,
        { id, role: 'assistant', content: '', events: [], ts: Date.now() },
      ],
    })),

  appendEvent: (id, event) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, events: [...m.events, event] } : m,
      ),
    })),

  appendMarkdownChunk: (id, chunk) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + chunk } : m,
      ),
    })),

  finalizeAssistantMessage: (id, final) =>
    set((state) => ({
      currentAssistantId: null,
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: final.markdown, final } : m,
      ),
    })),

  clear: () => set({ messages: [], currentAssistantId: null }),
}));
