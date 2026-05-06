import { test, expect, CHAT_SSE_DATA_FLOW } from './fixtures';

test.describe('/compare — fluxo de chat com mock SSE', () => {
  test('envia pergunta, recebe streaming e renderiza resposta completa', async ({
    page,
    mocks,
  }) => {
    await mocks.mockChatStream(CHAT_SSE_DATA_FLOW);
    await page.goto('/compare');

    // Digita pergunta no input
    const input = page.getByRole('textbox', { name: 'Pergunta' });
    await input.fill('Como BR vs FIN em gasto educacional 2020?');

    // Clica enviar
    await page.getByLabel('Enviar pergunta').click();

    // Mensagem do usuário aparece
    await expect(page.getByText('Como BR vs FIN em gasto educacional 2020?')).toBeVisible();

    // AgentReasoning timeline aparece (resumido — count) com Core e Retriever
    await expect(page.getByText(/2 etapas/)).toBeVisible();
    await expect(page.getByText('Core (Orchestrator + Profiler)')).toBeVisible();
    await expect(page.getByText('Retriever')).toBeVisible();

    // Markdown final renderiza
    await expect(
      page.getByRole('heading', { name: /Gasto educacional 2020/ }),
    ).toBeVisible();
    await expect(page.getByText(/5\.77% do PIB/)).toBeVisible();

    // Citação aparece com link doi.org (titulo aparece no card + ContextPanel
    // lateral — usar `.first()` para validar pelo menos uma ocorrencia)
    await expect(
      page.getByText('The Economics of International Differences in Educational Achievement').first(),
    ).toBeVisible();
    const doiLink = page.getByRole('link', { name: /Abrir DOI/ });
    await expect(doiLink).toHaveAttribute('href', 'https://doi.org/10.1162/REST_a_00081');
    await expect(doiLink).toHaveAttribute('target', '_blank');

    // Footer com fontes e follow-ups
    await expect(page.getByText(/Fontes:/)).toBeVisible();
    await expect(page.getByText(/Como evoluiu o gasto BR/)).toBeVisible();
  });

  test('auto-detecção de perfil aplica data-profile=researcher', async ({ page, mocks }) => {
    await mocks.mockChatStream(CHAT_SSE_DATA_FLOW);
    await page.goto('/compare');

    // Antes de enviar a pergunta, default eh researcher
    await expect(page.locator('html')).toHaveAttribute('data-profile', 'researcher');

    // Trocar para student manualmente para garantir que o auto-detect
    // NAO sobrescreve override manual
    await page.getByRole('button', { name: 'Estudante' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-profile', 'student');

    // Enviar pergunta
    await page
      .getByRole('textbox', { name: 'Pergunta' })
      .fill('Pergunta com perfil researcher detectado');
    await page.getByLabel('Enviar pergunta').click();

    // Aguarda resposta chegar (texto aparece no markdown + figcaption — pegar primeiro)
    await expect(page.getByText(/Gasto educacional 2020/).first()).toBeVisible();

    // Tema permanece student (override manual respeitado)
    await expect(page.locator('html')).toHaveAttribute('data-profile', 'student');
  });
});
