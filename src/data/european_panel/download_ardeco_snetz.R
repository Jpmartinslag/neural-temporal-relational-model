#!/usr/bin/env Rscript
# Download ARDECO SNETZ employment by industry (10 NACE sectors).
#
# This script intentionally avoids the CRAN ARDECO package because the current
# package requires R >= 4.2, while some project machines still run R 4.1.  It
# calls the same official ARDECO REST endpoint and reads the parquet payloads
# with the installed arrow package.
#
# Example:
#   Rscript src/data/european_panel/download_ardeco_snetz.R \
#     --countries FR,NL,BE,PT --years 2024

suppressPackageStartupMessages({
  library(arrow)
})

args <- commandArgs(trailingOnly = TRUE)

get_arg <- function(name, default) {
  idx <- which(args == name)
  if (length(idx) == 0 || idx == length(args)) return(default)
  args[idx + 1]
}

countries <- strsplit(get_arg("--countries", "FR,NL,BE,PT"), ",")[[1]]
years <- as.integer(strsplit(get_arg("--years", "2024"), ",")[[1]])
out_dir <- get_arg("--out-dir", "data/raw/european_panel/ardeco/snetz")

sectors <- c("A", "B-E", "F", "G-I", "J", "K", "L", "M_N", "O-Q", "R-U")
base_url <- "https://territorial.ec.europa.eu/ardeco-api-v2/rest/export/SNETZ"

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

all_rows <- list()
status_rows <- list()

for (country in countries) {
  for (year in years) {
    country_year_dir <- file.path(out_dir, paste0(country, "_", year))
    dir.create(country_year_dir, recursive = TRUE, showWarnings = FALSE)

    for (sector in sectors) {
      url <- paste0(
        base_url,
        "?unit=THS",
        "&sector=", URLencode(sector, reserved = TRUE),
        "&territory_id=", country,
        "&year=", year,
        "&level_id=3",
        "&version=2021",
        "&format=parquet"
      )
      raw_path <- file.path(country_year_dir, paste0("SNETZ_", country, "_", year, "_", gsub("/", "_", sector), ".parquet"))

      ok <- tryCatch({
        download.file(url, raw_path, quiet = TRUE, mode = "wb")
        TRUE
      }, error = function(e) FALSE)

      if (!ok) {
        status_rows[[length(status_rows) + 1]] <- data.frame(
          country = country, year = year, sector = sector,
          status = "download_fail", n = NA_integer_, zzz = NA_integer_,
          stringsAsFactors = FALSE
        )
        next
      }

      df <- tryCatch(read_parquet(raw_path), error = function(e) NULL)
      if (is.null(df)) {
        status_rows[[length(status_rows) + 1]] <- data.frame(
          country = country, year = year, sector = sector,
          status = "read_fail", n = NA_integer_, zzz = NA_integer_,
          stringsAsFactors = FALSE
        )
        next
      }

      zzz <- sum(grepl("ZZZ$", df$TERRITORY_ID))
      status_rows[[length(status_rows) + 1]] <- data.frame(
        country = country, year = year, sector = sector, status = "ok",
        n = nrow(df), zzz = zzz, stringsAsFactors = FALSE
      )

      df$COUNTRY_REQUEST <- country
      all_rows[[length(all_rows) + 1]] <- df
    }
  }
}

status <- do.call(rbind, status_rows)
status_path <- file.path(out_dir, "ardeco_snetz_download_status.csv")
write.csv(status, status_path, row.names = FALSE)

if (length(all_rows) > 0) {
  combined <- do.call(rbind, all_rows)
  combined_path <- file.path(out_dir, "ardeco_snetz_combined.csv")
  write.csv(combined, combined_path, row.names = FALSE)
}

print(status)
cat("\nSaved status:", status_path, "\n")
