import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InputBox } from '@/components/chat/InputBox';

describe('InputBox', () => {
  it('renders textarea with placeholder', () => {
    render(<InputBox onSubmit={() => {}} />);
    expect(screen.getByLabelText('Pergunta')).toBeInTheDocument();
  });

  it('calls onSubmit on Ctrl+Enter', () => {
    const onSubmit = vi.fn();
    render(<InputBox onSubmit={onSubmit} />);
    const textarea = screen.getByLabelText('Pergunta');
    fireEvent.change(textarea, { target: { value: 'Pergunta?' } });
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });
    expect(onSubmit).toHaveBeenCalledWith('Pergunta?');
  });

  it('does NOT submit on Enter without Ctrl', () => {
    const onSubmit = vi.fn();
    render(<InputBox onSubmit={onSubmit} />);
    const textarea = screen.getByLabelText('Pergunta');
    fireEvent.change(textarea, { target: { value: 'q' } });
    fireEvent.keyDown(textarea, { key: 'Enter' });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('disables button when value is empty', () => {
    render(<InputBox onSubmit={() => {}} />);
    const button = screen.getByLabelText('Enviar pergunta');
    expect(button).toBeDisabled();
  });

  it('disables both controls when disabled prop is true', () => {
    render(<InputBox onSubmit={() => {}} disabled />);
    expect(screen.getByLabelText('Pergunta')).toBeDisabled();
    expect(screen.getByLabelText('Enviar pergunta')).toBeDisabled();
  });

  it('clears textarea after submit', () => {
    const onSubmit = vi.fn();
    render(<InputBox onSubmit={onSubmit} />);
    const textarea = screen.getByLabelText('Pergunta') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'q' } });
    fireEvent.submit(textarea.closest('form')!);
    expect(textarea.value).toBe('');
  });

  it('honors initialValue prop', () => {
    render(<InputBox onSubmit={() => {}} initialValue="seed" />);
    const textarea = screen.getByLabelText('Pergunta') as HTMLTextAreaElement;
    expect(textarea.value).toBe('seed');
  });
});
