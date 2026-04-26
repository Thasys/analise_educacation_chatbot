# Bases de dados educacionais validadas academicamente: mapeamento completo para análise comparativa

**Para um sistema de análise e visualização de dados educacionais, a arquitetura mais eficiente combina três camadas**: APIs REST maduras (IBGE SIDRA, IPEADATA OData, World Bank, UIS, Eurostat, OECD SDMX, UK DfE) para indicadores agregados; **Base dos Dados/BigQuery** para microdados brasileiros harmonizados; e downloads estruturados (SAS/SPSS/CSV) do INEP e das avaliações internacionais (PISA, TIMSS, PIRLS) para análises de microdados. A principal descoberta deste levantamento é que, **apesar do discurso institucional de "dados abertos", o INEP não oferece API REST formal** — apenas downloads em ZIP —, enquanto OCDE, Eurostat, World Bank e UNESCO-UIS oferecem APIs SDMX/JSON robustas. Este relatório organiza 40+ bases em três categorias (Brasil, Internacional, Comparativa), com URL, formato, frequência e referências acadêmicas para cada uma.

---

## 1. Bases de dados sobre educação brasileira

**Observação metodológica**: No ecossistema brasileiro, APIs REST maduras existem apenas em IBGE SIDRA, IPEADATA OData e Base dos Dados (SQL via BigQuery). As fontes primárias do INEP exigem download em massa de arquivos ZIP com CSV/TXT e scripts SAS/SPSS.

### 1.1 INEP – Censo Escolar da Educação Básica
- **Instituição**: Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP/MEC)
- **Descrição**: Principal levantamento estatístico da educação básica. Pesquisa declaratória censitária cobrindo estabelecimentos, matrículas, turmas, alunos, docentes e gestores — educação infantil, fundamental, médio, EJA, especial e profissional. Microdados consolidados desde 2007 (sistema Educacenso); granularidade escola/município/UF/Brasil.
- **URL**: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar
- **API**: **Não há API REST formal**. Apenas downloads em ZIP (~10 GB/ano) e painéis BI no Inep Data.
- **Formato**: CSV pipe-delimitado com inputs SAS/SPSS; dicionários em PDF/XLSX.
- **Frequência**: Anual (referência: última quarta-feira de maio).
- **Referências**: Vizzotto (2020) *Ensaios Pedagógicos*; Alves & Soares (2013) *Educação e Pesquisa* v.39.

### 1.2 INEP – SAEB (Sistema de Avaliação da Educação Básica)
- **Instituição**: INEP/MEC
- **Descrição**: Avaliação em larga escala em Língua Portuguesa, Matemática (e Ciências em algumas edições) no 2º, 5º, 9º anos do EF e 3º ano do EM. Até 2017 incluía Prova Brasil (ANRESC, censitária em escolas públicas urbanas) e ANEB. Base do IDEB. Cobertura bienal desde 1995.
- **URL**: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/saeb
- **API**: Não. Download de microdados em ZIP; painel BI no Inep Data.
- **Formato**: CSV (pipe) + inputs SAS/SPSS; escalas de proficiência separadas.
- **Frequência**: Bienal (anos ímpares); última edição: 2023.
- **Referências**: Soares & Alves (2003) *Educação e Pesquisa* v.29 n.1; Alves & Soares (2013) sobre contexto escolar e indicadores.

### 1.3 INEP – ENEM
- **Instituição**: INEP/MEC
- **Descrição**: Exame voluntário anual, referência para ingresso no ensino superior. Microdados com notas, itens, gabaritos, questionário socioeconômico. Série desde 1998.
- **URL**: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem
- **API**: Não. Downloads em ZIP.
- **Formato**: CSV pipe, inputs SAS/SPSS.
- **Frequência**: Anual.
- **Referências**: Travitzki (2013) tese USP; artigos em *Educação & Realidade* e *Avaliação* (UNICAMP) sobre perfil socioeconômico.

### 1.4 INEP – IDEB (Índice de Desenvolvimento da Educação Básica)
- **Instituição**: INEP/MEC
- **Descrição**: Indicador sintético (criado em 2007) combinando fluxo escolar (Censo) e desempenho (SAEB). Metas bienais projetadas até 2021. Calculado para anos iniciais/finais do EF e EM, por escola/município/UF/Brasil.
- **URL**: https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb
- **API**: Não. Planilhas XLSX por escola/município/UF; consulta interativa no Inep Data.
- **Formato**: XLSX, ODS/CSV.
- **Frequência**: Bienal.
- **Referências**: Fernandes (2007) *Série Documental INEP* n.26; Soares & Xavier (2013) *Educação & Sociedade* v.34 n.124.

### 1.5 INEP – ENCCEJA
- **Instituição**: INEP/MEC
- **Descrição**: Exame de certificação de EF e EM para jovens/adultos (≥15 e ≥18 anos). Microdados com notas e questionário socioeconômico; desde 2002 (com interrupções).
- **URL**: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/encceja
- **API**: Não. Downloads em ZIP.
- **Formato**: CSV + SAS/SPSS.
- **Frequência**: Anual (irregular).
- **Referências**: Catelli Jr., Gisi & Serrao (2013) *Estudos em Avaliação Educacional* v.24 n.55.

### 1.6 IBGE – PNAD Contínua (módulo Educação)
- **Instituição**: Instituto Brasileiro de Geografia e Estatística
- **Descrição**: Pesquisa domiciliar amostral probabilística. **Módulo anual de Educação** (2º trimestre) cobre alfabetização, frequência a creche/escola, rede, nível de instrução, escolarização líquida, abandono, educação profissional. Dados trimestrais desde 2012; módulo ampliado desde 2016. Granularidade: Brasil, regiões, UFs, RMs, capitais.
- **URL**: https://www.ibge.gov.br/estatisticas/sociais/educacao/17270-pnad-continua.html
- **API**: **SIM — API SIDRA** (REST com JSON). Tabelas de educação: 7136-7139, 7141-7144, 7186-7188, 7210, 7224-7226, 9423. Base: `https://apisidra.ibge.gov.br/`. Pacotes `sidrapy` (Python) e `sidrar` (R). Microdados completos via FTP.
- **Formato**: Microdados TXT fixed-width + SAS/SPSS/R; agregados JSON/CSV.
- **Frequência**: Trimestral (educação básica); anual (módulo ampliado).
- **Referências**: Neri & Osório em publicações FGV Social sobre retornos à educação; Textos para Discussão IPEA (Costa & Ulyssea).
- **Coletor implementado** (Fase 1):
    - **Módulo**: [data_pipeline/src/collectors/ibge/sidra_educacao.py](data_pipeline/src/collectors/ibge/sidra_educacao.py)
    - **Flow Prefect**: [data_pipeline/src/flows/ibge_sidra.py](data_pipeline/src/flows/ibge_sidra.py) (`ingest_pnad_continua_t7136`)
    - **Tabela default**: 7136 — *Taxa de analfabetismo das pessoas de 15 anos ou mais, por sexo e cor/raça*.
    - **URL gerada**: `GET https://apisidra.ibge.gov.br/values/t/7136/n1/all/v/all/p/{ano}` (níveis territoriais e classificações configuráveis).
    - **Saída Bronze**: `/data/bronze/ibge/sidra_<tabela>/<ano>/data.parquet` (+ `_metadata.json` com SHA-256, schema, URL e timestamp UTC).
    - **Auditoria**: linha em `ingestion_log` (Postgres) por execução, com status `running → success|failed`.
    - **Notas**: parsing usa o cabeçalho retornado pela própria API para nomear colunas (ex.: `V`→`Valor`, `D1N`→`Brasil`). Coletor genérico — basta instanciar `SidraEducacaoCollector(table_id=7144, ...)` para outras tabelas da família.

### 1.7 IBGE – Censo Demográfico (variáveis de educação)
- **Instituição**: IBGE
- **Descrição**: Única fonte com cobertura municipal completa em variáveis educacionais populacionais (alfabetização, escolaridade, frequência escolar, curso concluído) em nível de setor censitário. Edições 1991, 2000, 2010, 2022.
- **URL**: https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html
- **API**: **SIM — SIDRA** (agregados); microdados via FTP.
- **Formato**: Microdados CSV/TXT; agregados SIDRA em JSON.
- **Frequência**: Decenal.
- **Referências**: Rios-Neto em publicações do CEDEPLAR/UFMG; notas técnicas do IPEA.

### 1.8 IPEADATA / Dados Abertos IPEA
- **Instituição**: Instituto de Pesquisa Econômica Aplicada (IPEA)
- **Descrição**: Repositório de séries históricas econômicas, sociais e regionais com centenas de indicadores educacionais derivados do INEP, IBGE e MEC: matrículas, escolarização, IDEB, analfabetismo, anos médios de estudo, gasto em educação. Granularidade: Brasil, UF, município.
- **URL**: http://www.ipeadata.gov.br/ ; https://dados.ipea.gov.br/
- **API**: **SIM — OData v4 RESTful**. URL base: `http://www.ipeadata.gov.br/api/odata4/`. Retorna JSON. Pacotes `ipeadatar` (R) e `ipeadatapy` (Python).
- **Formato**: JSON (API), CSV, XLSX.
- **Frequência**: Variável por série; atualização frequente.
- **Referências**: Soares & Osório em Textos para Discussão IPEA; artigos em *Pesquisa e Planejamento Econômico*.

### 1.9 Atlas do Desenvolvimento Humano no Brasil (IDHM Educação)
- **Instituição**: PNUD + IPEA + Fundação João Pinheiro
- **Descrição**: IDHM e suas dimensões (Educação, Longevidade, Renda) para 5.570 municípios, 27 UFs, 21 RMs e ~17 mil UDHs. **IDHM Educação** combina escolaridade adulta (25+ com EF completo) e fluxo escolar (5-20 anos). Mais de 330 indicadores socioeconômicos. Base: Censos 1991/2000/2010 (+ 2022 em processo).
- **URL**: http://www.atlasbrasil.org.br/
- **API**: Não há API REST formal. Consulta interativa e exportação CSV/XLSX; versão tratada na Base dos Dados/BigQuery.
- **Formato**: CSV, XLSX, PDF.
- **Frequência**: Decenal (Radar IDHM anual via PNAD).
- **Referências**: PNUD/IPEA/FJP (2013) *Atlas do Desenvolvimento Humano no Brasil*; Cardoso & Lage em *Nova Economia*.

### 1.10 Base dos Dados
- **Instituição**: Associação Base dos Dados (sem fins lucrativos) + parceria Google Cloud
- **Descrição**: Data lake público no Google BigQuery com datasets oficiais **harmonizados** (Censo Escolar 2009+, IDEB, SAEB, ENEM, PNAD/PNADC, Censo Demográfico, Atlas). É a via programática mais usada academicamente para microdados brasileiros integrados.
- **URL**: https://basedosdados.org/
- **API**: **SIM de facto** — SQL direto via BigQuery + pacotes `basedosdados` em Python, R e Stata.
- **Formato**: Tabelas SQL; download CSV/Parquet.
- **Frequência**: Acompanha fontes primárias.
- **Referências**: Adotada em pesquisas recentes em economia da educação (FGV EPGE, Insper, USP).

### 1.11 Portal Brasileiro de Dados Abertos (dados.gov.br)
- **Instituição**: CGU / Ministério da Gestão
- **Descrição**: Catálogo CKAN federado agregando datasets do INEP, FNDE (FUNDEB, merenda, transporte), MEC e IBGE. Atua como espelho/catálogo dos microdados INEP e programas federais (PDDE, PNAE, PNLD).
- **URL**: https://dados.gov.br/
- **API**: **SIM — CKAN REST** (`/api/3/action/package_search`). Metadados em JSON; arquivos redirecionam para os órgãos-fonte.
- **Formato**: JSON (metadados), CSV/XLSX/ZIP (dados).
- **Frequência**: Variável por dataset.

### 1.12 QEdu
- **Instituição**: Instituto Iede (anteriormente Meritt + Fundação Lemann)
- **Descrição**: Agregador que reprocessa e visualiza dados do INEP (Censo Escolar, SAEB, IDEB, ENEM) e PNAD Contínua. Mostra aprendizado adequado, reprovação, distorção idade-série, infraestrutura e NSE por escola/município/estado.
- **URL**: https://qedu.org.br/
- **API**: **Não disponibiliza API REST pública**. Downloads limitados em alguns formatos.
- **Formato**: HTML, XLSX/CSV parciais.
- **Frequência**: Acompanha INEP.
- **Referências**: Citado em dissertações CAPES sobre gestão escolar (FEUSP, UFMG).

### 1.13 Observatório do PNE (Todos Pela Educação)
- **Instituição**: Movimento Todos Pela Educação + 29 organizações parceiras
- **Descrição**: Monitora as 20 metas e 254 estratégias do PNE (Lei 13.005/2014) com indicadores derivados de INEP, IBGE e SIOPE. Recortes por raça/cor, renda, idade.
- **URL**: https://www.observatoriodopne.org.br/
- **API**: Não. Dossiês em PDF/XLSX.
- **Formato**: HTML, PDF, XLSX.
- **Frequência**: Acompanha fontes primárias.
- **Referências**: Dourado (2017) *Série PNE em Movimento – INEP*; artigos em *Retratos da Escola*.

### 1.14 FGV Social / CPS
- **Instituição**: Fundação Getulio Vargas – IBRE (direção Marcelo Neri)
- **Descrição**: Produtor de indicadores derivados sobre educação, renda, desigualdade, mobilidade intergeracional. Usa PNAD/PNADC, Censo, RAIS, IRPF.
- **URL**: https://cps.fgv.br/
- **API**: Não. Relatórios em PDF, microsites interativos.
- **Formato**: PDF, XLSX, HTML.
- **Frequência**: Por projeto.
- **Referências**: Neri (2009) *Motivos da Evasão Escolar*, FGV; Neri & Bonomo em *Income Distribution Dynamics in Brazil* (FGV/Springer).

### 1.15 SARESP / IDESP (SEDUC-SP)
- **Instituição**: Secretaria da Educação de São Paulo (SEDUC-SP) / CIMA
- **Descrição**: SARESP avalia 3º, 5º, 7º e 9º anos do EF e 3º EM em Língua Portuguesa, Matemática e Ciências em escolas estaduais/municipais/amostra de privadas. IDESP combina SARESP + fluxo. Série desde 1996 (SARESP); IDESP desde 2007; microdados por aluno disponíveis 2011-2022.
- **URL**: https://dados.educacao.sp.gov.br/
- **API**: Parcial (CKAN do Dados Abertos SP com URLs diretas de CSV).
- **Formato**: CSV com dicionários próprios.
- **Frequência**: Anual.
- **Referências**: Ferrão & Almeida em *Estudos em Avaliação Educacional* (FCC); Bauer, Alavarse & Oliveira em *Educação e Pesquisa* v.41.

### 1.16 Outras bases estaduais e complementares
Incluem **SAEPE** (Pernambuco), **SIMAVE/PROEB** (Minas Gerais), **SPAECE** (Ceará) — muitos operados pelo **CAEd/UFJF** (https://www.caedufjf.net/); **Dados Abertos da Prefeitura de SP – SME** (https://dados.prefeitura.sp.gov.br/organization/educacao1, com IDEP municipal e CKAN); **SIOPE/FNDE** (https://www.fnde.gov.br/siope/, gastos em educação, CSV/XLSX); **PeNSE** (Pesquisa Nacional de Saúde do Escolar, IBGE+MS); **Censo da Educação Superior/INEP** para análise de licenciaturas. A maioria oferece apenas download PDF/XLSX, sem API.

---

## 2. Bases de dados sobre educação internacional (OCDE, Europa, EUA)

**Observação crítica**: O antigo endpoint `stats.oecd.org` foi descontinuado em **01/07/2024** e substituído pelo **OECD Data Explorer** com API SDMX em `sdmx.oecd.org`. Sistemas legados precisam migração. UIS, OECD e Eurostat conduzem coleta conjunta via **UOE Data Collection**, então indicadores macro são idênticos nas três bases — escolha pela ergonomia da API.

### 2.1 OECD Data Explorer / OECD.Stat
- **Instituição**: OECD – Directorate for Education and Skills
- **Descrição**: Plataforma central de todos os datasets OECD, incluindo dataflows "Education and Skills" (matrícula, financiamento, professores, resultados, mobilidade). Cobre 38 membros + parceiros (Brasil, Rússia, G20). Séries desde 1990-2000.
- **URL**: https://data-explorer.oecd.org/
- **API**: **SIM — REST SDMX 2.1**. Endpoint: `https://sdmx.oecd.org/public/rest/`. Sem autenticação, **rate limit 60 queries/hora/IP**. Documentação: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html. Pacotes R: `rsdmx`, `OECD`.
- **Formato**: SDMX-ML, SDMX-JSON, CSV (`csvfile`, `csvfilewithlabels`), XML.
- **Frequência**: Anual (por dataset).
- **Referências**: Hanushek & Woessmann (2011) *Economic Policy* 26(67); OECD (2025) *Education at a Glance 2025*.

### 2.2 OECD Education GPS / Education at a Glance / INES
- **Instituição**: OECD – INES Programme
- **Descrição**: Portal interativo e publicação anual com 100+ indicadores comparativos para todos países OCDE + parceiros (Brasil é membro INES). Coleta via **UOE Data Collection** (UIS/OECD/Eurostat). Cobre ECEC, ISCED 1-3, VET e terciário.
- **URL**: https://gpseducation.oecd.org/ ; https://www.oecd.org/education/education-at-a-glance/
- **API**: Via SDMX do Data Explorer; perfis país exportáveis em Excel/PDF.
- **Formato**: PDF, Excel, SDMX.
- **Frequência**: Anual (setembro).
- **Referências**: Schleicher (2019) *World Class*, OECD Publishing; Woessmann (2016) *Journal of Economic Perspectives* 30(3).

### 2.3 OECD PISA
- **Instituição**: OECD
- **Descrição**: Avaliação trienal de alunos de 15 anos em leitura, matemática, ciências + domínios inovadores (resolução colaborativa 2015, competência global 2018, pensamento criativo 2022, Media & AI Literacy 2025). 90+ países em PISA 2025. Microdados com 10 plausible values e pesos BRR.
- **URL**: https://www.oecd.org/pisa/ ; https://www.oecd.org/en/data/datasets/pisa-2022-database.html
- **API**: Não dedicada; agregados via OECD Data Explorer SDMX. Microdados por download direto.
- **Formato**: SAS, SPSS, TXT (ciclos antigos), codebooks PDF. Pacotes R: `intsvy`, `learningtower`, `EdSurvey`; Stata: `repest`, `pisatools`; software oficial: IEA IDB Analyzer.
- **Frequência**: Trienal.
- **Referências**: Hanushek & Woessmann (2012) *Journal of Economic Growth* 17(4); Jerrim et al. (2017) *Economics of Education Review* 61.

### 2.4 OECD TALIS (Teaching and Learning International Survey)
- **Instituição**: OECD
- **Descrição**: Maior pesquisa internacional sobre professores e diretores (condições de trabalho, desenvolvimento profissional, práticas pedagógicas). Foco ISCED 2, com módulos para ISCED 1 e 3. **TALIS Starting Strong** cobre ECEC. Ciclos 2008, 2013, 2018, 2024 (55 sistemas; ~280 mil professores).
- **URL**: https://www.oecd.org/en/about/programmes/talis.html
- **API**: Agregados via Data Explorer; microdados por download.
- **Formato**: SPSS, Stata, SAS (TALIS 2024 inclui CSV e R).
- **Frequência**: Quinquenal.
- **Referências**: OECD (2020) *TALIS 2018 Results Volume II*; Sims & Jerrim (2020) *UCL Institute of Education*.

### 2.5 UNESCO UIS
- **Instituição**: UNESCO Institute for Statistics (Montréal) — custódio do SDG 4
- **Descrição**: 4.000+ indicadores sobre matrícula, professores, financiamento, alfabetização e SDG 4. ISCED 0-8, 200+ países desde ~1970. Produtos: SDG 4 indicators, OPRI, R&D, Cultura. Classificação ISCED 2011.
- **URL**: https://databrowser.uis.unesco.org/ ; https://apiportal.uis.unesco.org/
- **API**: **SIM — Data API** (documentada) + **Bulk Data Download Service (BDDS)**. Limite 100.000 registros/query; sem autenticação obrigatória. Pacote R: `uisapi`.
- **Formato**: CSV (BDDS), JSON, Excel.
- **Frequência**: Atualizações semestrais (fev/set/nov).
- **Referências**: Altinok, Angrist & Patrinos (2018) *World Bank WP* 8314; UNESCO *Global Education Monitoring Report* (usa UIS como fonte primária).

### 2.6 Eurostat – Education and Training Statistics
- **Instituição**: Eurostat (Comissão Europeia)
- **Descrição**: Estatísticas harmonizadas para 27 EM da UE + EFTA + candidatos (ISCED 0-8). Participação, alunos, professores, financiamento, mobilidade, aprendizagem de línguas. Granularidade nacional e **NUTS 1/2/3**.
- **URL**: https://ec.europa.eu/eurostat/web/education-and-training/database
- **API**: **SIM — DUAS APIs REST**: (1) **API Statistics** em JSON-stat (`https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{datasetCode}`); (2) **SDMX 2.1 e 3.0**. Sem autenticação; reuso livre. Pacote R: `eurostat` (rOpenGov).
- **Formato**: JSON-stat, SDMX-ML, CSV/TSV, Excel.
- **Frequência**: Anual (UOE).
- **Referências**: Fernández-Macías & Hurley (2017) *Socio-Economic Review* 15(3); Lahti et al. (2017) *The R Journal* 9(1).

### 2.7 NCES – Common Core of Data (CCD, EUA)
- **Instituição**: National Center for Education Statistics / IES / US Department of Education
- **Descrição**: Censo anual universal de todas as escolas públicas, distritos e agências estaduais dos EUA + territórios (Nonfiscal + Fiscal). Séries desde 1986-87.
- **URL**: https://nces.ed.gov/ccd/
- **API**: Não oficial. **API de terceiros confiável**: **Urban Institute Education Data API** (https://educationdata.urban.org/documentation/) cobre CCD, CRDC, IPEDS, EDFacts, College Scorecard.
- **Formato**: CSV, ASCII, SAS.
- **Frequência**: Anual.

### 2.8 NCES – NAEP (The Nation's Report Card)
- **Instituição**: NCES
- **Descrição**: Avaliação representativa nacional/estadual de alunos das séries 4, 8 e 12 em leitura, matemática, ciências, escrita, história, cívica. Main NAEP desde 1990; Long-Term Trend desde 1971; TUDA (distritos urbanos).
- **URL**: https://nces.ed.gov/nationsreportcard/ ; https://www.nationsreportcard.gov/
- **API**: **SIM — NAEP Data Service API** (REST/JSON): https://www.nationsreportcard.gov/api_documentation.aspx. Microdados restritos por licença IES.
- **Formato**: JSON (API), CSV/Excel (via NDE). Software: EdSurvey (R), NAEPEX, AM.
- **Frequência**: Bienal (matemática/leitura).
- **Referências**: Reardon (2011) em *Whither Opportunity?* Russell Sage.

### 2.9 NCES – ECLS, Digest, EDFacts
- **ECLS (Early Childhood Longitudinal Study)**: estudos longitudinais desde nascimento/kindergarten (ECLS-B, ECLS-K:1998/2011/2024). URL: https://nces.ed.gov/ecls/. Formato SPSS/SAS/Stata; sem API; restricted-use via IES.
- **Digest of Education Statistics**: compilação anual com ~400 tabelas pré-escola à pós-graduação. URL: https://nces.ed.gov/programs/digest/. HTML/Excel/PDF.
- **EDFacts**: reporte administrativo mandatório (matrícula, graduação, absenteísmo, assessments). URL: https://www2.ed.gov/about/inits/ed/edfacts/data-files/index.html. CSV; parcialmente via API do Urban Institute.
- **Referências**: Chetty, Friedman & Rockoff (2014) *American Economic Review* 104(9).

### 2.10 World Bank EdStats
- **Instituição**: World Bank Group
- **Descrição**: 4.000+ indicadores agregando UIS, OECD, TIMSS, PIRLS, PISA, DHS, MICS, SABER, LSMS. Cobre 200+ economias desde 1970.
- **URL**: https://datatopics.worldbank.org/education/ ; https://data360.worldbank.org/en/dataset/WB_EDSTATS
- **API**: **SIM — uma das APIs mais robustas do mundo**: `https://api.worldbank.org/v2/`, JSON/XML, sem autenticação. Data360 nova API (beta). Pacotes R: `WDI`, `wbstats`; Python: `wbdata`, `world_bank_data`.
- **Formato**: JSON, XML, CSV/Excel, SDMX (Data360).
- **Frequência**: Anual (alinhada ao UOE).
- **Referências**: Barro & Lee (2013) *Journal of Development Economics* 104; Filmer & Rogers (2018) *World Development Report 2018: Learning to Realize Education's Promise*.
- **Coletor implementado** (Fase 1):
    - **Módulo**: [data_pipeline/src/collectors/worldbank/api_client.py](data_pipeline/src/collectors/worldbank/api_client.py)
    - **Flow Prefect**: [data_pipeline/src/flows/worldbank.py](data_pipeline/src/flows/worldbank.py) (`ingest_education_indicators`)
    - **Endpoint**: `GET https://api.worldbank.org/v2/country/{países}/indicator/{ID}?date={ano|range}&format=json` — paginação automática até 50 páginas; sem autenticação.
    - **Indicadores acompanhados na cesta default**: `SE.XPD.TOTL.GD.ZS` (gasto em educação % PIB), `SE.PRM.CMPT.ZS` (conclusão primária), `SE.PRM.ENRR` / `SE.SEC.ENRR` (matrícula bruta), `SE.ADT.LITR.ZS` (alfabetização adulta), `HD.HCI.OVRL` (Human Capital Index).
    - **Saída Bronze**: `/data/bronze/worldbank/indicator_<id_em_snake>/<período>/data.parquet`. Schema achatado: `indicator_id, indicator_name, country_id, country_name, country_iso3, date, value, unit, obs_status, decimal`.
    - **Períodos**: aceita ano único (`"2023"`) ou range (`"2010-2023"`) — convertido internamente para `2010:2023` na URL e preservado com `-` no path (compatível com Windows).
- **Instituição**: IEA (Amsterdã/Hamburgo), com centros internacionais (Boston College para TIMSS/PIRLS, ACER para ICCS)
- **Descrição**: **TIMSS** – matemática e ciências, 4º e 8º ano, quadrienal (1995, 1999, 2003, 2007, 2011, 2015, 2019, 2023, 2027). **PIRLS** – leitura, 4º ano, quinquenal (2001-2026). **ICCS** – cidadania, 8º ano (2009, 2016, 2022). **ICILS** – letramento computacional e pensamento computacional, 8º ano (2013, 2018, 2023, 2028).
- **URL**: https://www.iea.nl/studies/iea/ ; https://timssandpirls.bc.edu/ ; https://timss2023.org/data/
- **API**: Não. Downloads do IEA Study Data Repository com aceite de termos. Software IEA IDB Analyzer.
- **Formato**: SPSS, SAS, R (desde TIMSS 2023). Pacotes R: `intsvy`, `RALSA`, `EdSurvey`.
- **Frequência**: Quadrienal (TIMSS) / Quinquenal (demais).
- **Referências**: Mullis et al. (2020, 2023) *TIMSS/PIRLS International Reports*; Woessmann (2003) *Oxford Bulletin*; Fraillon et al. (2020) *Preparing for Life in a Digital World* (Springer open access).

### 2.12 Eurydice (Comissão Europeia)
- **Instituição**: European Education and Culture Executive Agency (EACEA) — rede de 43 unidades nacionais
- **Descrição**: Rede de **informação qualitativa-comparativa** sobre sistemas educacionais europeus. Eurypedia (descrições por país em 14 capítulos padronizados), estudos temáticos, **Key Data on Education** (indicadores estruturais), calendários escolares, salários de professores. ISCED 0-8.
- **URL**: https://eurydice.eacea.ec.europa.eu/
- **API**: **Não há API**. PDFs, Eurypedia (HTML), alguns Excel em Key Data.
- **Formato**: PDF, HTML.
- **Frequência**: Eurypedia anual; estudos ad hoc.
- **Referências**: West & Nikolai (2013) *Journal of Social Policy* 42(3).

### 2.13 UK Department for Education – Explore Education Statistics
- **Instituição**: UK Department for Education (Inglaterra)
- **Descrição**: Estatísticas oficiais do DfE: absenteísmo, exclusões, performance (Key Stages 1, 2, 4, 5), School Workforce Census, financiamento, destinos pós-escolares, SEN. Granularidade nacional/regional/LA/escola (URN).
- **URL**: https://explore-education-statistics.service.gov.uk/
- **API**: **SIM — REST com GET+POST** (queries complexas com AND/OR/NOT): `https://api.education.gov.uk/statistics/v1/`. Docs: https://api.education.gov.uk/statistics/docs/. Sem autenticação; Open Government License v3. SDK R: `eesyapi`.
- **Formato**: CSV, JSON.
- **Frequência**: Por publicação.
- **Referências**: Burgess, Wilson & Worth (2013) *Journal of Public Economics* 106; Allen & Sims (2018) *The Teacher Gap*, Routledge.

### 2.14 Bases complementares internacionais
- **Urban Institute Education Data Portal** (https://educationdata.urban.org/) — API REST gratuita harmonizando CCD, CRDC, SAIPE, IPEDS, College Scorecard.
- **ILSA-Gateway** (https://ilsa-gateway.org/) — meta-catálogo IEA/DIPF de todas as avaliações internacionais de larga escala.
- **CivicLEADS ICPSR** (https://www.icpsr.umich.edu/web/civicleads/) — arquivo para ICCS e educação cívica.

---

## 3. Bases de dados comparativas Brasil × internacional

A tabela abaixo consolida a **participação brasileira** nas principais avaliações internacionais de educação básica:

| Avaliação | Brasil participa? | Ciclos com Brasil | Nível |
|---|---|---|---|
| PISA | **Sim, desde 2000 (todos os ciclos)** | 2000 a 2022, próximo 2025 | 15 anos (fim EF/início EM) |
| TIMSS | **Parcialmente** | 1995, 2003, 2023 (retorno), 2027 | 4º e 8º ano |
| PIRLS | **Sim, desde 2021** | 2021, 2026 confirmado | 4º ano |
| ICCS | **Sim** | 2009, 2016, 2022 | 8º ano |
| ICILS | **Não** | — | 8º ano |
| PIAAC | **Não** | — | Adultos 16-65 |
| ERCE/TERCE/SERCE | **Sim em todos os ciclos** | SERCE 2006, TERCE 2013, ERCE 2019 | 3º e 6º ano |
| TALIS | **Sim** | 2013, 2018, 2024 | Professores ISCED 1-3 |

### 3.1 PISA (detalhes comparativos Brasil)
Brasil foi o **primeiro país não-membro a aderir** (1998). Permite comparações Brasil × OCDE, Brasil × América Latina (Argentina, Chile, Colômbia, México, Peru, Uruguai) e Brasil × mundo. Indicadores: pontuações por domínio, níveis de proficiência (1-6), ESCS, clima escolar, repetência, bem-estar.
- **URL Brasil**: https://www.oecd.org/en/about/programmes/pisa/brazil.html
- **Referências brasileiras**: Carnoy, Khavenson, Costa & Marotta (2015) *Cadernos de Pesquisa* 45(157); Horta Neto (2024) *Educar em Revista* — "As fragilidades do PISA"; Klein, R. "Uma re-análise dos resultados do PISA" em *Ensaio*.

### 3.2 TIMSS (comparativo Brasil)
Brasil participou de TIMSS 1995 e 2003, retornou em **TIMSS 2023** (primeira participação regular em duas décadas) e está confirmado para **TIMSS 2027**. Permite comparação com 64 países e tendências de 28 anos.
- **URL**: https://timss2023.org/data/
- **Referências**: Mullis & Martin (2020) *TIMSS 2019 International Results*; Fishbein et al. (2025) *TIMSS 2023 User Guide*.

### 3.3 PIRLS (comparativo Brasil)
Brasil participou pela primeira vez em **PIRLS 2021** (com anotação "2" por exclusões entre 5-10% da população elegível), confirmado para **PIRLS 2026**. Mais de 60 países em 2021. SDG 4.1.1b é calculado a partir de PIRLS.
- **URL**: https://www.iea.nl/studies/iea/pirls/2021
- **Referências**: Mullis et al. (2023) *PIRLS 2021 International Results in Reading*, Boston College.

### 3.4 ICCS (comparativo Brasil)
Brasil participou de **ICCS 2009, 2016 e 2022**. No ICCS 2022 houve taxas abaixo do padrão no survey de professores. Inclui módulo regional latino-americano.
- **URL**: https://www.iea.nl/studies/iea/iccs/2022 ; DOI ICCS 2022: https://doi.org/10.58150/ICCS_2022_data_edition_2_including_process_data
- **Referências**: Schulz et al. (2023) *ICCS 2022 International Report*, IEA.

### 3.5 ERCE/LLECE (principal comparativo latino-americano)
- **Instituição**: Laboratorio Latinoamericano de Evaluación (LLECE) – OREALC/UNESCO Santiago
- **Descrição**: Avalia 3º e 6º ano em Leitura, Escrita, Matemática, Ciências Naturais (+ habilidades socioemocionais em 2019). Alinhado aos indicadores SDG 4.1.1a e 4.1.1b. **Brasil participa em todos os ciclos**: SERCE 2006, TERCE 2013, ERCE 2019 (16 países).
- **URL**: https://llecesunesco.org/ ; https://github.com/llece/erce
- **API**: Sem API oficial, mas **microdados abertos em GitHub oficial** (llece/erce) com CSV; bases completas em CSV/SPSS via portal LLECE.
- **Formato**: CSV, SPSS (metodologia BRR).
- **Frequência**: ~6-7 anos (PERCE 1997, SERCE 2006, TERCE 2013, ERCE 2019, ERCE 2025).
- **Referências**: UNESCO-OREALC (2021) *Los aprendizajes fundamentales en América Latina y el Caribe: ERCE 2019*; Medeiros, Jaloto & Santos (2017) comparação PISA 2015 × TERCE em *Revista Eletrônica de Educação*.

### 3.6 PIAAC (limitação importante)
Brasil **NÃO participou** do Ciclo 1 (2011-2018) nem do Ciclo 2 Round 1 (2022-2023). Países latino-americanos participantes: Chile, Ecuador, México, Peru, Colômbia (Ciclo 1); Chile (Ciclo 2). Comparações indiretas com Brasil usam **INAF** (Indicador de Alfabetismo Funcional, Instituto Paulo Montenegro) como análogo nacional.
- **URL**: https://www.oecd.org/en/about/programmes/piaac.html

### 3.7 OECD Education at a Glance – Brasil
Brasil é **país parceiro que participa formalmente do INES** (um dos poucos não-OCDE). Country Notes específicos do Brasil em cada edição. Edições recentes: 2022 (terciário), 2023 (EPT/VET), 2024 (equidade), 2025.
- **URL EAG 2025 Brasil**: https://www.oecd.org/en/publications/education-at-a-glance-2025_1a3543e2-en/brazil_d42263a0-en.html
- **API**: OECD Data Explorer SDMX (conforme §2.1).
- **Referências**: OECD (2024) *Education at a Glance 2024*, https://doi.org/10.1787/c00cad36-en; OECD *Handbook for Internationally Comparative Education Statistics 2018*.

### 3.8 UNESCO GEM Report (Global Education Monitoring)
Relatório independente da UNESCO que monitora o SDG 4 com três ferramentas: **SCOPE** (progresso), **WIDE** (World Inequality Database on Education) e **PEER** (perfis nacionais). Brasil e 200+ países; relatório 2026 focará equidade na contagem regressiva para 2030.
- **URL**: https://www.unesco.org/gem-report/en ; https://www.education-inequalities.org/
- **API**: Sem API REST; dados em CSV via SCOPE; exportação no WIDE. Subjacentes no UIS.
- **Referências**: UNESCO (2020) *GEM Report 2020: Inclusion and Education — All means all*; UNESCO (2021/2) *Non-state actors in education*.

### 3.9 CEPALSTAT (comparativo América Latina)
- **Instituição**: CEPAL/ECLAC (ONU)
- **Descrição**: Portal com 2.000+ indicadores harmonizados para ALC, incluindo educação (alfabetização, anos de estudo, conclusão, gastos, NEET, ODS 4). Permite Brasil × demais países ALC.
- **URL**: https://statistics.cepal.org/portal/cepalstat/
- **API**: **SIM — Open Data API CEPALSTAT** (https://statistics.cepal.org/portal/cepalstat/open-data.html). Sistema REDATAM para censos.
- **Formato**: JSON, XML, Excel, CSV.
- **Frequência**: Contínua.
- **Referências**: CEPAL/UNESCO (2020) *La educación en tiempos de la pandemia de COVID-19*; Trucco em CEPAL Serie Políticas Sociales.

### 3.10 Human Capital Index (HCI) – World Bank
Índice composto (0-1) de capital humano aos 18 anos. **Componente educação**: anos esperados e anos ajustados pela qualidade (harmonized test scores). Brasil incluído em toda a série (2018, 2020, 2023; HCI+ 2026 incluirá emprego).
- **URL**: https://www.worldbank.org/en/publication/human-capital ; indicador WDI `HD.HCI.OVRL`
- **API**: **SIM — via API World Bank** (conforme §2.10).
- **Frequência**: Bianual.
- **Referências**: Kraay (2019) *World Bank Research Observer* 34(1); Angrist, Djankov, Goldberg & Patrinos (2021) *Nature* 592 — "Measuring human capital using global learning data".

### 3.11 Barro-Lee Educational Attainment Dataset
- **Instituição**: Robert Barro (Harvard) e Jong-Wha Lee (Korea University)
- **Descrição**: Base clássica de atainment educacional para 146 países, 1950-2010, em intervalos de 5 anos, desagregada por sexo e faixa etária, com 7 níveis ISCED. Brasil incluído em toda a série.
- **URL**: http://barrolee.com/ ; https://barrolee.github.io/BarroLeeDataSet/
- **API**: Não. Downloads em XLS, CSV, DTA. Espelhado no World Bank EdStats.
- **Frequência**: Irregular (2010, 2013, 2021 estendendo até 2015).
- **Referências**: Barro & Lee (2013) *Journal of Development Economics* 104; Barro & Lee (2015) *Education Matters* (Oxford University Press).

### 3.12 Harmonized Learning Outcomes (HLO) – World Bank
Base que **harmoniza resultados de PISA, TIMSS, PIRLS, ERCE e SACMEQ** em uma escala comum — fundamental para comparar países que participam de apenas uma avaliação regional (como Brasil pré-2021 no ERCE + PISA).
- **Referência seminal**: Angrist, Djankov, Goldberg & Patrinos (2021) *Nature* 592, 403-408.

---

## Resumo da acessibilidade programática — decisão arquitetural

| Categoria | Fonte | API REST | Formato principal | Recomendação para o sistema |
|---|---|---|---|---|
| Brasil | IBGE SIDRA | ✅ JSON | JSON/CSV | **Core** para agregados |
| Brasil | IPEADATA | ✅ OData v4 | JSON | **Core** para séries históricas |
| Brasil | Base dos Dados | ✅ (BigQuery SQL) | SQL/CSV/Parquet | **Core** para microdados INEP |
| Brasil | INEP (direto) | ❌ | CSV+SAS/SPSS | Baseline oficial |
| Brasil | dados.gov.br | ✅ CKAN | JSON (metadados) | Catálogo complementar |
| Internacional | World Bank | ✅ (robusta) | JSON/XML/CSV | **Core** cobertura global |
| Internacional | UNESCO UIS | ✅ + BDDS | CSV/JSON | **Core** SDG 4 |
| Internacional | Eurostat | ✅ JSON-stat + SDMX | JSON-stat | **Core** Europa |
| Internacional | OECD Data Explorer | ✅ SDMX | SDMX-JSON/CSV | **Core** OCDE (cuidado rate limit) |
| Internacional | UK DfE | ✅ GET+POST | CSV/JSON | Complementar Reino Unido |
| Internacional | NCES NAEP | ✅ | JSON | Complementar EUA |
| Comparativo | CEPALSTAT | ✅ | JSON/XML | **Core** América Latina |
| Microdados | PISA/TIMSS/PIRLS/ICCS/TALIS | ❌ | SPSS/SAS/R | ETL batch com `intsvy`, `EdSurvey` |
| Microdados | ERCE | ❌ (mas GitHub) | CSV/SPSS | Via repositório llece/erce |

## Considerações finais e recomendações

**Arquitetura sugerida para o sistema**: (1) camada de ingestão assíncrona para as APIs REST maduras (IBGE SIDRA, IPEADATA, World Bank, UIS, Eurostat, OECD SDMX, CEPALSTAT, UK DfE); (2) conexão SQL/BigQuery com a **Base dos Dados** para microdados brasileiros harmonizados; (3) pipeline ETL em lote para microdados de avaliações internacionais (PISA, TIMSS, PIRLS, ICCS, TALIS, ERCE), usando pacotes `intsvy`, `EdSurvey`, `RALSA` e o IEA IDB Analyzer — respeitando a metodologia de plausible values e pesos replicativos (BRR/Jackknife).

**Três alertas metodológicos críticos**: (1) o endpoint antigo `stats.oecd.org` foi descontinuado em julho/2024 — qualquer biblioteca legada quebrará; (2) o **INEP não possui API REST formal**, apesar de marketing institucional em contrário — o acesso programático real depende de downloads em ZIP ou da mediação da Base dos Dados; (3) comparações temporais Brasil × TIMSS têm **ruptura de duas décadas** entre 2003 e 2023, e Brasil **não participa** do ICILS nem do PIAAC, exigindo uso do HLO (Angrist et al., 2021) ou de análogos nacionais (INAF para adultos; TIC Educação/CETIC.br para letramento digital) quando essas dimensões forem relevantes.

**Para comparações Brasil × mundo focadas em educação básica**, a combinação mais robusta e citada academicamente é: **PISA (desempenho cognitivo 15 anos)** + **ERCE (desempenho 3º/6º ano na ALC)** + **PIRLS 2021 (leitura 4º ano)** + **TIMSS 2023/2027 (matemática e ciências)** + **UNESCO UIS (indicadores SDG 4 agregados)** + **OECD Education at a Glance (sistema educacional comparado)** + **World Bank HCI (qualidade ajustada ao atainment)**. Esse conjunto cobre desempenho, acesso, equidade, qualidade e sistema, e todos os seus indicadores-chave podem ser acessados programaticamente ou via downloads estruturados reprodutíveis.