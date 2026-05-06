import { Sidebar } from '@/components/layout/Sidebar';
import { Workspace } from '@/components/layout/Workspace';
import { ContextPanel } from '@/components/layout/ContextPanel';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Biblioteca de citações acumuladas — Sprint 6.4 implementa.
 */
export default function LibraryPage() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <Workspace>
        <div className="flex flex-1 items-center justify-center p-6">
          <Card className="max-w-md border-dashed">
            <CardHeader>
              <CardTitle>Biblioteca de citações</CardTitle>
              <CardDescription>
                Histórico de DOIs citados pelos agentes durante a sessão.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Implementação prevista no Sprint 6.4.
            </CardContent>
          </Card>
        </div>
      </Workspace>
      <ContextPanel />
    </div>
  );
}
