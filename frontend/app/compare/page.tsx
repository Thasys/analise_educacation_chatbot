import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { Chat } from '@/components/chat/Chat';

/**
 * Pagina principal — chat de analise comparada.
 *
 * Layout 3 colunas via WorkspaceShell. Conteudo:
 *   - Chat conectado a streamChat (SSE) com auto-deteccao de perfil.
 *   - InlineChart Plotly + CitationPanel embarcado em cada resposta.
 */
export default function ComparePage() {
  return (
    <WorkspaceShell>
      <Chat />
    </WorkspaceShell>
  );
}
