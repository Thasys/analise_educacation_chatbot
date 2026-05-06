import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentReasoning } from '@/components/chat/AgentReasoning';
import type { StreamEvent } from '@/types/domain';

describe('AgentReasoning', () => {
  it('renders nothing when no events and not loading', () => {
    const { container } = render(<AgentReasoning events={[]} loading={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('builds timeline from agent_started + agent_done events', () => {
    const events: StreamEvent[] = [
      { type: 'agent_started', agent: 'Core', ts: 1 },
      {
        type: 'agent_done',
        agent: 'Core',
        ts: 2,
        result: { flow: 'data', profile: 'researcher' },
      },
      { type: 'agent_started', agent: 'Retriever', ts: 3 },
      {
        type: 'agent_done',
        agent: 'Retriever',
        ts: 4,
        tool_calls: 2,
      },
    ];
    render(<AgentReasoning events={events} loading={false} />);
    expect(screen.getByText('Core')).toBeInTheDocument();
    expect(screen.getByText('Retriever')).toBeInTheDocument();
    expect(screen.getByText(/2 tool call\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/flow=data/)).toBeInTheDocument();
  });

  it('shows count in trigger label', () => {
    const events: StreamEvent[] = [
      { type: 'agent_started', agent: 'A', ts: 1 },
      { type: 'agent_started', agent: 'B', ts: 2 },
    ];
    render(<AgentReasoning events={events} loading={true} />);
    expect(screen.getByText(/2 etapas/)).toBeInTheDocument();
  });

  it('singularizes "etapa" when count is 1', () => {
    const events: StreamEvent[] = [{ type: 'agent_started', agent: 'A', ts: 1 }];
    render(<AgentReasoning events={events} loading={true} />);
    expect(screen.getByText(/1 etapa/)).toBeInTheDocument();
  });

  it('marks last entry as error when error event present', () => {
    const events: StreamEvent[] = [
      { type: 'agent_started', agent: 'Core', ts: 1 },
      { type: 'error', error: 'boom', ts: 2 },
    ];
    render(<AgentReasoning events={events} loading={false} />);
    expect(screen.getByLabelText('erro')).toBeInTheDocument();
  });
});
