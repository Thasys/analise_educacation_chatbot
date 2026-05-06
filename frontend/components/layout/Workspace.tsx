import type { ReactNode } from 'react';
import { cn } from '@/lib/utils/cn';

interface WorkspaceProps {
  children: ReactNode;
  className?: string;
}

export function Workspace({ children, className }: WorkspaceProps) {
  return (
    <main className={cn('flex h-full flex-1 flex-col overflow-hidden', className)}>{children}</main>
  );
}
