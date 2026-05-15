import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { DataExplorer } from '@/components/explorer/DataExplorer';

/**
 * Explorador de marts Gold — DataExplorer consome /api/data/catalog
 * via TanStack Query e mostra lista + detalhe dentro do WorkspaceShell.
 */
export default function ExplorerPage() {
  return (
    <WorkspaceShell>
      <DataExplorer />
    </WorkspaceShell>
  );
}
