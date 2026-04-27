#!/usr/bin/env Rscript
# =============================================================================
# PIRLS — extração de agregados de leitura com plausible values + Jackknife.
#
# Uso:
#   Rscript pirls_extraction.R 2021
#
# Brasil participou pela primeira vez em 2021, então não há séries históricas
# nacionais para o estudo PIRLS antes desse ciclo.
#
# Saída: data/bronze/iea/pirls/<year>/data.parquet
# =============================================================================

suppressPackageStartupMessages({
  library(EdSurvey)
  library(intsvy)
  library(arrow)
  library(dplyr)
  library(fs)
  library(jsonlite)
  library(logger)
})

source("_packages.R")
install_missing(required_packages)

args <- commandArgs(trailingOnly = TRUE)
years <- as.integer(args)
if (length(years) == 0) {
  stop("Uso: Rscript pirls_extraction.R <year>")
}

data_root <- Sys.getenv("DATA_ROOT", unset = "../data")
cache_dir <- path(data_root, "_cache", "iea", "pirls")
bronze_root <- path(data_root, "bronze", "iea", "pirls")
dir_create(cache_dir, recurse = TRUE)
dir_create(bronze_root, recurse = TRUE)

extract_pirls <- function(year) {
  log_info("PIRLS {year} — baixando microdados (cache em {cache_dir})")
  downloadPIRLS(years = year, root = cache_dir, cache = TRUE)
  pirls_data <- readPIRLS(path = cache_dir, countries = "*", year = year)

  log_info("PIRLS {year} — média de leitura (PV1..PV5 + Jackknife)")
  means <- intsvy::pirls.mean.pv(
    pvlabel = "READ",
    by      = "CNT",
    data    = pirls_data
  )

  results <- means %>%
    rename(
      REF_AREA  = CNT,
      OBS_VALUE = Mean,
      SE        = `Std. err.`,
      N         = `Freq.`
    ) %>%
    mutate(
      study = "PIRLS",
      TIME_PERIOD = as.character(year),
      domain = "reading"
    ) %>%
    select(study, REF_AREA, TIME_PERIOD, domain, OBS_VALUE, SE, N)

  out_dir <- path(bronze_root, as.character(year))
  dir_create(out_dir, recurse = TRUE)
  parquet_path <- path(out_dir, "data.parquet")
  arrow::write_parquet(results, parquet_path, compression = "zstd")

  metadata <- list(
    source           = "iea",
    dataset          = "pirls",
    reference_period = as.character(year),
    ingested_at      = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    source_url       = "https://pirls2021.org/results/",
    row_count        = nrow(results),
    column_count     = ncol(results),
    parquet_path     = as.character(parquet_path),
    methodology      = "intsvy::pirls.mean.pv with PV1..PV5 + Jackknife weights",
    extra            = list(domain = "reading")
  )
  write_json(
    metadata, path(out_dir, "_metadata.json"),
    auto_unbox = TRUE, pretty = TRUE
  )
  log_info("PIRLS {year} — escrito em {parquet_path} ({nrow(results)} linhas)")
  invisible(results)
}

for (year in years) {
  tryCatch(
    extract_pirls(year),
    error = function(e) log_error("PIRLS {year} falhou: {conditionMessage(e)}")
  )
}
