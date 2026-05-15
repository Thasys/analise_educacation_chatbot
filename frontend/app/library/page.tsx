import { WorkspaceShell } from '@/components/layout/WorkspaceShell';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Biblioteca de citações acumuladas — pagina ainda em placeholder.
 * Implementacao futura: lista DOIs acumulados na sessao com filtro
 * por ano/fonte/perfil.
 */
export default function LibraryPage() {
  return (
    <WorkspaceShell>
      <div className="flex flex-1 items-center justify-center p-6">
        <Card className="max-w-md border-dashed">
          <CardHeader>
            <CardTitle>Biblioteca de citações</CardTitle>
            <CardDescription>
              Histórico de DOIs citados pelos agentes durante a sessão.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Em desenvolvimento.
          </CardContent>
        </Card>
      </div>
    </WorkspaceShell>
  );
}
