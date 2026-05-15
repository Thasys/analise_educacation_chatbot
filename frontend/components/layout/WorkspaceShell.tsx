import type { ReactNode } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Workspace } from '@/components/layout/Workspace';
import { ContextPanel } from '@/components/layout/ContextPanel';

interface WorkspaceShellProps {
  children: ReactNode;
}

/**
 * Shell de 3 colunas (Sidebar + Workspace + ContextPanel).
 *
 * Centraliza a estrutura repetida em /compare, /explorer e /library
 * (DRY #9.1). Adicionar uma nova pagina vira:
 *
 *     <WorkspaceShell>
 *       <MyNewFeature />
 *     </WorkspaceShell>
 *
 * Em vez de copiar o div flex + 3 imports + 3 tags.
 */
export function WorkspaceShell({ children }: WorkspaceShellProps) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <Workspace>{children}</Workspace>
      <ContextPanel />
    </div>
  );
}
