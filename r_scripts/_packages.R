# =============================================================================
# Pacotes R canônicos para extração de microdados PISA/TIMSS/PIRLS.
# Reproduzir com: source("_packages.R"); renv::snapshot()
# =============================================================================

required_packages <- c(
  # Avaliações internacionais — plausible values + BRR/Jackknife corretos.
  "EdSurvey",     # NCES — PISA, TIMSS, PIRLS, NAEP. Ref: NCES (2024).
  "intsvy",       # CRAN — pisa.mean.pv, timss.mean.pv, etc.
  "RALSA",        # análises com pesos replicados.

  # I/O — leitura de microdados oficiais (SPSS) e escrita Parquet.
  "haven",        # read_spss / read_sav.
  "arrow",        # write_parquet (Apache Arrow).
  "fs",           # path manipulation portátil.

  # Utilitários — manipulação tabular e logging.
  "dplyr",
  "tidyr",
  "readr",
  "purrr",
  "logger"
)

install_missing <- function(pkgs) {
  to_install <- pkgs[!pkgs %in% rownames(installed.packages())]
  if (length(to_install) > 0) {
    message("Instalando: ", paste(to_install, collapse = ", "))
    install.packages(to_install)
  }
}

if (sys.nframe() == 0L) {
  install_missing(required_packages)
}
