#!/usr/bin/env bash
#
# Detect configuration drift between GitHub and the Terraform configuration
#
# Runs a full-refresh `terraform plan -detailed-exitcode`, converts the plan to
# JSON with `terraform show -json` and summarises it with scripts/drift_report.py.
# Run it from a directory where `terraform init` has been done, with GitHub
# credentials in the environment (e.g. GITHUB_TOKEN) and the module's required
# variables set. From this repository's root that means
# `export TF_VAR_config_path="$PWD/config"` (the Makefile does it for you).
# The refresh is never skipped: a plan without it cannot see out-of-band
# changes. The plan also contains configuration changes that are merged but not
# yet applied, so run it against applied configuration for a drift-only signal.
#
# Usage:
#   ./scripts/detect-drift.sh [OPTIONS]
#
# Options:
#   -f, --format FORMAT   Report format: text (default), markdown or json
#   -p, --plan-file PATH  Write the binary plan to PATH and keep it. Without
#                         this option a temporary file is used and removed.
#                         A plan file can contain secrets; treat it as one.
#   -r, --repo NAME       Limit the plan to one repository (same -target as
#                         `make plan-repo`)
#   -h, --help            Show this help message
#
# Exit codes (the report goes to stdout, progress and errors to stderr):
#   0  no drift
#   1  error (missing tool, failed plan, invalid plan JSON, bad option)
#   2  drift: the plan changes at least one resource
#   3  critical drift: a github_repository would be destroyed or replaced
#
# Whether the plan has changes is decided from the plan JSON, not from the
# terraform exit status alone: output-only changes make terraform exit 2 but
# are not drift.
#
# Examples:
#   ./scripts/detect-drift.sh
#   ./scripts/detect-drift.sh --format markdown --plan-file drift.tfplan
#   ./scripts/detect-drift.sh --repo my-repo --format json
#
# Requirements:
#   - terraform, initialized in the current directory
#   - python3
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_SCRIPT="$SCRIPT_DIR/drift_report.py"

if [[ -t 2 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
    PLAN_COLOR=()
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
    PLAN_COLOR=(-no-color)
fi

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

usage() {
    sed -n '3,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

FORMAT="text"
PLAN_FILE=""
REPO=""

require_value() {
    if [[ $# -lt 2 || -z "${2:-}" ]]; then
        log_error "Option $1 requires a value"
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f | --format)
            require_value "$@"
            FORMAT="$2"
            shift 2
            ;;
        -p | --plan-file)
            require_value "$@"
            PLAN_FILE="$2"
            shift 2
            ;;
        -r | --repo)
            require_value "$@"
            REPO="$2"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage >&2
            exit 1
            ;;
    esac
done

case "$FORMAT" in
    text | markdown | json) ;;
    *)
        log_error "Unsupported format '$FORMAT' (use text, markdown or json)"
        exit 1
        ;;
esac

if [[ -n "$REPO" && ! "$REPO" =~ ^[A-Za-z0-9._-]+$ ]]; then
    log_error "Invalid repository name '$REPO'"
    exit 1
fi

for tool in terraform python3; do
    if ! command -v "$tool" > /dev/null 2>&1; then
        log_error "$tool is required but was not found in PATH"
        exit 1
    fi
done

if [[ -z "$PLAN_FILE" ]]; then
    PLAN_FILE="$(mktemp)"
    trap 'rm -f "$PLAN_FILE"' EXIT
fi

plan_args=(plan -detailed-exitcode -input=false ${PLAN_COLOR[@]+"${PLAN_COLOR[@]}"} -out="$PLAN_FILE")
if [[ -n "$REPO" ]]; then
    plan_args+=("-target=module.repositories[\"${REPO}\"]")
    log_info "Planning repository $REPO with a full refresh..."
else
    log_info "Planning all managed resources with a full refresh..."
fi

plan_rc=0
terraform "${plan_args[@]}" >&2 || plan_rc=$?
if [[ $plan_rc -ne 0 && $plan_rc -ne 2 ]]; then
    log_error "terraform plan failed (exit $plan_rc)"
    exit 1
fi

log_info "Reading the plan..."
if ! plan_json="$(terraform show -json "$PLAN_FILE")"; then
    log_error "terraform show failed"
    exit 1
fi

report_rc=0
printf '%s' "$plan_json" | python3 "$REPORT_SCRIPT" - --format "$FORMAT" || report_rc=$?

case "$report_rc" in
    0)
        if [[ $plan_rc -eq 2 ]]; then
            log_info "terraform reported changes, but none affect resources; not drift"
        fi
        log_success "No drift detected"
        ;;
    2)
        log_warn "Drift detected"
        ;;
    3)
        log_error "Critical drift: a repository would be destroyed or replaced"
        ;;
    *)
        log_error "Could not build the drift report (exit $report_rc)"
        exit 1
        ;;
esac

exit "$report_rc"
