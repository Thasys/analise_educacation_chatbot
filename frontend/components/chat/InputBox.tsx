'use client';

import { useState, type KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface InputBoxProps {
  onSubmit: (question: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** Texto inicial (ex.: pergunta de exemplo clicada na home). */
  initialValue?: string;
}

export function InputBox({
  onSubmit,
  disabled = false,
  placeholder = 'Faça sua pergunta sobre educação comparada...',
  initialValue = '',
}: InputBoxProps) {
  const [value, setValue] = useState(initialValue);

  const handleSubmit = (): void => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    // Ctrl+Enter (ou Cmd+Enter) envia; Enter sozinho insere quebra de linha.
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form
      className="mx-auto flex max-w-2xl items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
    >
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={1}
        disabled={disabled}
        aria-label="Pergunta"
        className="min-h-[44px] flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      />
      <Button
        type="submit"
        size="icon"
        disabled={disabled || !value.trim()}
        aria-label="Enviar pergunta"
      >
        <Send className="h-4 w-4" aria-hidden />
      </Button>
    </form>
  );
}
