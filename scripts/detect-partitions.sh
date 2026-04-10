#!/usr/bin/env bash
# detect-partitions.sh — Map git diff output to affected Terraform partitions.
#
# Usage:
#   ./scripts/detect-partitions.sh [--tfvar] [--help] [<git-diff-range>]
#
# Arguments:
#   <git-diff-range>  Git rev range passed to git diff --name-only (e.g. main...HEAD).
#                     Defaults to HEAD (staged + unstaged changes against HEAD).
#
# Flags:
#   --tfvar   Output as a JSON array (e.g. ["infra","platform"]) instead of one-per-line.
#   --help    Show this help message and exit.
#
# Exit codes:
#   0  Success (including "no config changes" case — empty output signals no plan needed).
#   1  Error (e.g. git command failed).
#
# Assumptions:
#   - Repository config files live under config/repository/
#   - Partition subdirectories are one level deep: config/repository/<partition>/*.yml
#   - Shared config directories: config/group/, config/ruleset/, config/webhook/, config/config.yml
#   - This script is run from the repository root.
#
# Escalation rules:
#   1. Shared config changes  → output ALL partition names (any repo may be affected)
#   2. Partition-specific     → output only the changed partitions
#   3. Top-level repo files   → no partitions (always loaded, no partition plan needed)
#   4. No config changes      → empty output, exit 0

set -eo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

TFVAR=false
DIFF_RANGE=""

for arg in "$@"; do
  case "$arg" in
    --help|-h)
      sed -n '2,/^$/p' "$0" | grep '^#' | sed 's/^# \?//'
      exit 0
      ;;
    --tfvar)
      TFVAR=true
      ;;
    -*)
      echo "Unknown flag: $arg" >&2
      echo "Run with --help for usage." >&2
      exit 1
      ;;
    *)
      DIFF_RANGE="$arg"
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Collect changed files
# ---------------------------------------------------------------------------

if [[ -n "$DIFF_RANGE" ]]; then
  changed_files=$(git diff --name-only "$DIFF_RANGE" 2>/dev/null) || {
    echo "Error: git diff failed for range '$DIFF_RANGE'" >&2
    exit 1
  }
else
  # Default: uncommitted changes (staged + unstaged) against HEAD
  changed_files=$(git diff --name-only HEAD 2>/dev/null) || {
    echo "Error: git diff failed" >&2
    exit 1
  }
fi

# ---------------------------------------------------------------------------
# Classify changed files
# ---------------------------------------------------------------------------

shared_change=false
partition_list=""  # newline-separated partition names

while IFS= read -r file; do
  [[ -z "$file" ]] && continue

  # Shared config: any change here requires planning all partitions
  if [[ "$file" == config/config.yml ]] \
      || [[ "$file" == config/group/* ]] \
      || [[ "$file" == config/ruleset/* ]] \
      || [[ "$file" == config/webhook/* ]]; then
    shared_change=true

  # Partition-specific repo file: config/repository/<partition>/<file>.yml
  elif [[ "$file" =~ ^config/repository/([^/]+)/[^/]+\.yml$ ]]; then
    partition="${BASH_REMATCH[1]}"
    partition_list="${partition_list}${partition}"$'\n'

  # Top-level repo file: config/repository/<file>.yml — always loaded, no partition needed
  elif [[ "$file" =~ ^config/repository/[^/]+\.yml$ ]]; then
    : # no-op

  fi
done <<< "$changed_files"

# ---------------------------------------------------------------------------
# Apply escalation: shared config overrides partition-specific
# ---------------------------------------------------------------------------

if [[ "$shared_change" == true ]]; then
  # Output all known partitions (discover from filesystem)
  repo_config_dir="config/repository"
  if [[ ! -d "$repo_config_dir" ]]; then
    echo "Error: directory '$repo_config_dir' not found. Run from the repository root." >&2
    exit 1
  fi
  result=$(find "$repo_config_dir" -mindepth 1 -maxdepth 1 -type d -print0 \
    | sort -z \
    | xargs -0 -I{} basename {})
elif [[ -n "$partition_list" ]]; then
  # Deduplicate and sort
  result=$(echo "$partition_list" | sort -u | grep -v '^$')
else
  # No config changes that require a partition plan
  result=""
fi

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

if [[ "$TFVAR" == true ]]; then
  # JSON array format for use as TF_VAR_repository_partitions
  if [[ -z "$result" ]]; then
    echo "[]"
  else
    # Build JSON array from newline-separated list
    json="["
    first=true
    while IFS= read -r item; do
      [[ -z "$item" ]] && continue
      if [[ "$first" == true ]]; then
        json="${json}\"${item}\""
        first=false
      else
        json="${json},\"${item}\""
      fi
    done <<< "$result"
    json="${json}]"
    echo "$json"
  fi
else
  # One partition per line
  if [[ -n "$result" ]]; then
    echo "$result"
  fi
fi
