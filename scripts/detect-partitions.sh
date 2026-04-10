#!/usr/bin/env bash
# detect-partitions.sh — Map git diff output to affected Terraform partitions.
#
# Usage:
#   ./scripts/detect-partitions.sh [--tfvar] [--help] [<git-diff-range>]
#
# Arguments:
#   <git-diff-range>  Git rev range passed to git diff --name-only (e.g. main...HEAD).
#                     Defaults to HEAD (tracked file changes vs HEAD).
#
# Flags:
#   --tfvar   Output as a JSON array (e.g. ["infra","platform"]) instead of one-per-line.
#             Requires jq. Empty output becomes "[]".
#   --help    Show this help message and exit.
#
# Exit codes:
#   0  Success (including "no config changes" case — empty output signals no plan needed).
#   1  Error (e.g. git command failed, jq not found).
#
# Assumptions:
#   - Repository config files live under config/repository/
#   - Partition subdirectories are one level deep: config/repository/<partition>/*.yml
#   - Only directories containing at least one *.yml file are considered partitions
#     (matches Terraform's repository_partition_dirs discovery logic)
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

if [[ "$TFVAR" == true ]] && ! command -v jq &>/dev/null; then
  echo "Error: --tfvar requires jq. Install it (e.g. apt install jq / brew install jq)." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Collect changed files
# ---------------------------------------------------------------------------

if [[ -n "$DIFF_RANGE" ]]; then
  changed_files=$(git diff --name-only "$DIFF_RANGE" 2>/dev/null) || {
    echo "Error: git diff failed for range '$DIFF_RANGE'" >&2
    exit 1
  }
else
  # Default: tracked file changes vs HEAD (does not include untracked files)
  changed_files=$(git diff --name-only HEAD 2>/dev/null) || {
    echo "Error: git diff failed" >&2
    exit 1
  }
fi

# ---------------------------------------------------------------------------
# Discover known partitions (dirs containing at least one *.yml — matches
# Terraform's repository_partition_dirs logic which uses fileset("*/*.yml"))
# ---------------------------------------------------------------------------

repo_config_dir="config/repository"
if [[ ! -d "$repo_config_dir" ]]; then
  echo "Error: directory '$repo_config_dir' not found. Run from the repository root." >&2
  exit 1
fi

known_partitions=$(find "$repo_config_dir" -mindepth 2 -maxdepth 2 -name "*.yml" \
  | sed "s|^$repo_config_dir/||" \
  | cut -d/ -f1 \
  | sort -u)

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
  # All known partitions (only dirs with *.yml, matching Terraform's discovery)
  result="$known_partitions"
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
  # JSON array via jq — handles any characters in partition names correctly
  if [[ -z "$result" ]]; then
    echo "[]"
  else
    echo "$result" | jq -R -s -c 'split("\n") | map(select(length > 0))'
  fi
else
  # One partition per line
  if [[ -n "$result" ]]; then
    echo "$result"
  fi
fi
