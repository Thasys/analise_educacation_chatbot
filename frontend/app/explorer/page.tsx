import { Sidebar } from '@/components/layout/Sidebar';
import { Workspace } from '@/components/layout/Workspace';
import { ContextPanel } from '@/components/layout/ContextPanel';
import { DataExplorer } from '@/components/explorer/DataExplorer';

/**
 * Explorador de marts Gold.
 *
 * Sprint 6.0: shell (3 colunas + placeholder).
 * Sprint 6.4: <DataExplorer> consumindo /api/data/catalog (TanStack Query).
 */
export default function ExplorerPage() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <Workspace>
        <DataExplorer />
      </Workspace>
      <ContextPanel />
    </div>
  );
}
