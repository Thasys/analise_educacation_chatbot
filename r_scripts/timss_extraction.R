#!/usr/bin/env Rscript
# =============================================================================
# TIMSS — extração de agregados com plausible values + Jackknife.
#
# Uso:
#   Rscript timss_extraction.R 2023
#
# Brasil tem participação registrada em 1995, 1999, 2003 e 2023. A lacuna
# 2007–2019 deve ser tratada com ressalvas explícitas em qualquer análise
# de tendência.
#
# Saída: data/bronze/iea/timss/<year>/data.parquet
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
  stop("Uso: Rscript timss_extraction.R <year> [year2 ...]")
}

data_root <- Sys.getenv("DATA_ROOT", unset = "../data")
cache_dir <- path(data_root, "_cache", "iea", "timss")
bronze_root <- path(data_root, "bronze", "iea", "timss")
dir_create(cache_dir, recurse = TRUE)
dir_create(bronze_root, recurse = TRUE)

extract_timss <- function(year) {
  log_info("TIMSS {year} — baixando microdados (cache em {cache_dir})")
  downloadTIMSS(years = year, root = cache_dir, cache = TRUE)

  # Grades: 4 (séries iniciais) e 8 (séries finais). Iteramos os dois para
  # cobrir os recortes oficiais; nem todo país participa nos dois.
  grade_results <- purrr::map_dfr(c(4, 8), function(grade) {
    timss_data <- readTIMSS(path = cache_dir, countries = "*", gradeLvl = grade, year = year)

    domains <- list(
      math    = "MATH",
      science = "SCIE"
    )

    purrr::map_dfr(names(domains), function(domain) {
      log_info("TIMSS {year} grade {grade} — média {domain} (PV1..PV5 + Jackknife)")
      means <- intsvy::timss.mean.pv(
        pvlabel = domains[[domain]],
        by      = "CNT",
        data    = timss_data
      )
      means$domain <- domain
      means$grade  <- grade
      means$year   <- year
      means
    })
  })

  results <- grade_results %>%
    rename(
      REF_AREA  = CNT,
      OBS_VALUE = Mean,
      SE        = `Std. err.`,
      N         = `Freq.`
    ) %>%
    mutate(
      study = "TIMSS",
      TIME_PERIOD = as.character(year)
    ) %>%
    select(study, REF_AREA, TIME_PERIOD, grade, domain, OBS_VALUE, SE, N)

  out_dir <- path(bronze_root, as.character(year))
  dir_create(out_dir, recurse = TRUE)
  parquet_path <- path(out_dir, "data.parquet")
  arrow::write_parquet(results, parquet_path, compression = "zstd")

  metadata <- list(
    source           = "iea",
    dataset          = "timss",
    reference_period = as.character(year),
    ingested_at      = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    source_url       = sprintf("https://timss2023.org/results/data/", year),
    row_count        = nrow(results),
    column_count     = ncol(results),
    parquet_path     = as.character(parquet_path),
    methodology      = "intsvy::timss.mean.pv with PV1..PV5 + Jackknife weights",
    extra            = list(grades = c(4, 8), domains = c("math", "science"))
  )
  write_json(
    metadata, path(out_dir, "_metadata.json"),
    auto_unbox = TRUE, pretty = TRUE
  )
  log_info("TIMSS {year} — escrito em {parquet_path} ({nrow(results)} linhas)")
  invisible(results)
}

for (year in years) {
  tryCatch(
    extract_timss(year),
    error = function(e) log_error("TIMSS {year} falhou: {conditionMessage(e)}")
  )
}
