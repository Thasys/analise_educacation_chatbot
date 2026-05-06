import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combina classes condicionais e resolve conflitos do Tailwind.
 *
 * Exemplo:
 *   cn('px-2', condition && 'bg-primary', 'px-4') -> 'bg-primary px-4'
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
