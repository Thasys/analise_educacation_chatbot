import { Sidebar } from '@/components/layout/Sidebar';
import { Workspace } from '@/components/layout/Workspace';
import { ContextPanel } from '@/components/layout/ContextPanel';
import { Chat } from '@/components/chat/Chat';

/**
 * Pagina principal — chat de analise comparada.
 *
 * Sprint 6.0: scaffold + 3 colunas + placeholder.
 * Sprint 6.2: Chat real conectado a streamChat + auto-deteccao de perfil.
 * Sprint 6.3: <InlineChart> Plotly + <CitationPanel> embarcado nas respostas.
 */
export default function ComparePage() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <Workspace>
        <Chat />
      </Workspace>
      <ContextPanel />
    </div>
  );
}
