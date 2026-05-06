import { test, expect, SAMPLE_CATALOG } from './fixtures';

test.describe('/explorer — DataExplorer', () => {
  test('renderiza catálogo e detalhe ao clicar em mart', async ({ page, mocks }) => {
    await mocks.mockCatalog(SAMPLE_CATALOG);
    await page.goto('/explorer');

    // Header da pagina
    await expect(
      page.getByRole('heading', { name: 'Explorador de marts Gold' }),
    ).toBeVisible();

    // 3 cards na lista
    await expect(page.getByText('br_vs_ocde__gasto_educacao_timeseries')).toBeVisible();
    await expect(page.getByText('alfabetizacao__latam_2020s')).toBeVisible();
    await expect(page.getByText('indicadores__rankings_recente')).toBeVisible();

    // Sumario
    await expect(page.getByText('3 de 3 marts')).toBeVisible();

    // Estado inicial: nenhum selecionado
    await expect(page.getByText(/Selecione um mart à esquerda/)).toBeVisible();

    // Clicar no primeiro mart abre detalhe
    await page.getByText('br_vs_ocde__gasto_educacao_timeseries').click();
    await expect(
      page.getByRole('heading', { name: 'mart_br_vs_ocde__gasto_educacao_timeseries' }),
    ).toBeVisible();
    // Heading numerico do detalhe (linhas e colunas)
    await expect(page.getByRole('heading', { name: '491', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: '18', exact: true })).toBeVisible();
  });

  test('filtra marts por texto', async ({ page, mocks }) => {
    await mocks.mockCatalog(SAMPLE_CATALOG);
    await page.goto('/explorer');

    await expect(page.getByText('3 de 3 marts')).toBeVisible();

    await page.getByLabel('Buscar mart').fill('alfab');
    await expect(page.getByText('1 de 3 marts')).toBeVisible();
    await expect(page.getByText('alfabetizacao__latam_2020s')).toBeVisible();
    await expect(
      page.getByText('br_vs_ocde__gasto_educacao_timeseries'),
    ).not.toBeVisible();
  });

  test('mostra estado de erro com retry quando catálogo falha', async ({ page, mocks }) => {
    await mocks.mockCatalogError(500);
    await page.goto('/explorer');

    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByText('Falha ao carregar o catálogo')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Tentar novamente' })).toBeVisible();
  });
});
