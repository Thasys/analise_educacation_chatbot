#!/usr/bin/env Rscript
# =============================================================================
# PISA — extração de agregados com plausible values + BRR/Jackknife.
#
# Uso:
#   Rscript pisa_extraction.R 2018 2022
#
# Saída: data/bronze/iea/pisa/<year>/data.parquet
#        data/bronze/iea/pisa/<year>/_metadata.json (proveniência)
#
# Domínios calculados: matemática, leitura, ciências (médias por país +
# erros-padrão BRR conforme PISA Data Analysis Manual, OECD 2024).
# =============================================================================

suppressPackageStartupMessages({
  library(EdSurvey)
  library(intsvy)
  library(arrow)
  library(dplyr)
  library(tidyr)
  library(fs)
  library(jsonlite)
  library(logger)
})

source("_packages.R")
install_missing(required_packages)

args <- commandArgs(trailingOnly = TRUE)
years <- as.integer(args)
if (length(years) == 0) {
  stop("Uso: Rscript pisa_extraction.R <year1> [year2 ...]")
}

# Resolução de caminhos baseada em DATA_ROOT (mesmo contrato do .env do projeto).
data_root <- Sys.getenv("DATA_ROOT", unset = "../data")
cache_dir <- path(data_root, "_cache", "iea", "pisa")
bronze_root <- path(data_root, "bronze", "iea", "pisa")
dir_create(cache_dir, recurse = TRUE)
dir_create(bronze_root, recurse = TRUE)

extract_pisa <- function(year) {
  log_info("PISA {year} — baixando microdados (cache em {cache_dir})")

  # EdSurvey::downloadPISA é idempotente; pula download se o ano já está em cache.
  downloadPISA(years = year, root = cache_dir, cache = TRUE)
  pisa_data <- readPISA(path = cache_dir, countries = "*", database = "INT", year = year)

  # Médias por país — pacote intsvy aplica BRR/Jackknife automaticamente.
  # Saídas com colunas: country, mean, se_mean (erro-padrão), n.
  domains <- list(
    math    = "PV1MATH",
    read    = "PV1READ",
    science = "PV1SCIE"
  )

  results <- purrr::map_dfr(names(domains), function(domain) {
    log_info("PISA {year} — calculando média {domain} (PV1..PV10 + BRR)")
    means <- intsvy::pisa.mean.pv(
      pvlabel = sub("^PV1", "", domains[[domain]]),  # "MATH" / "READ" / "SCIE"
      by      = "CNT",                                # país (ISO-3 alpha)
      data    = pisa_data
    )
    means$domain <- domain
    means$year   <- year
    means
  })

  # Renomeia para schema canônico do projeto (alinha com OBS_VALUE/REF_AREA).
  results <- results %>%
    rename(
      REF_AREA   = CNT,
      OBS_VALUE  = Mean,
      SE         = `Std. err.`,
      N          = `Freq.`
    ) %>%
    mutate(
      study = "PISA",
      TIME_PERIOD = as.character(year)
    ) %>%
    select(study, REF_AREA, TIME_PERIOD, domain, OBS_VALUE, SE, N)

  # Persistência: Parquet + sidecar de metadados (mesma convenção que a Bronze
  # do data_pipeline Python).
  out_dir <- path(bronze_root, as.character(year))
  dir_create(out_dir, recurse = TRUE)
  parquet_path <- path(out_dir, "data.parquet")
  arrow::write_parquet(results, parquet_path, compression = "zstd")

  metadata <- list(
    source           = "iea",
    dataset          = "pisa",
    reference_period = as.character(year),
    ingested_at      = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    source_url       = sprintf("https://www.oecd.org/pisa/data/%s/", year),
    row_count        = nrow(results),
    column_count     = ncol(results),
    parquet_path     = as.character(parquet_path),
    methodology      = "intsvy::pisa.mean.pv with PV1..PV10 + BRR weights",
    extra            = list(domains = names(domains))
  )
  write_json(
    metadata, path(out_dir, "_metadata.json"),
    auto_unbox = TRUE, pretty = TRUE
  )
  log_info("PISA {year} — escrito em {parquet_path} ({nrow(results)} linhas)")
  invisible(results)
}

for (year in years) {
  tryCatch(
    extract_pisa(year),
    error = function(e) log_error("PISA {year} falhou: {conditionMessage(e)}")
  )
}
