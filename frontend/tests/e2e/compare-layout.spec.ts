import { test, expect } from './fixtures';

test.describe('/compare — layout e seletor de perfil', () => {
  test('redirecionamento de / para /compare', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/compare$/);
  });

  test('renderiza 3 colunas e header com seletor de perfil', async ({ page }) => {
    await page.goto('/compare');
    // Header
    await expect(
      page.getByRole('heading', { name: 'Análise Educacional Comparada' }),
    ).toBeVisible();
    // Sidebar (link Comparar)
    await expect(page.getByRole('link', { name: 'Comparar' })).toBeVisible();
    // Seletor de perfil — 3 botoes
    await expect(page.getByRole('button', { name: 'Pesquisador' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Gestor público' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Estudante' })).toBeVisible();
    // Empty state
    await expect(page.getByText('Pronto para perguntar')).toBeVisible();
  });

  test('mudança de perfil aplica data-profile no <html>', async ({ page }) => {
    await page.goto('/compare');

    // Inicial: researcher (default)
    await expect(page.locator('html')).toHaveAttribute('data-profile', 'researcher');

    // Click em Estudante
    await page.getByRole('button', { name: 'Estudante' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-profile', 'student');

    // Click em Gestor público
    await page.getByRole('button', { name: 'Gestor público' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-profile', 'policy');
  });

  test('clicar em pergunta de exemplo popula o input', async ({ page }) => {
    await page.goto('/compare');
    const sampleQuestion = 'Como o Brasil se compara com a Finlândia em gasto educacional em 2020?';
    await page.getByRole('button', { name: sampleQuestion }).click();

    const input = page.getByRole('textbox', { name: 'Pergunta' });
    await expect(input).toHaveValue(sampleQuestion);
  });
});
