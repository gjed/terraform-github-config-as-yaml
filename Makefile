.PHONY: help init plan plan-repo plan-show plan-pr apply apply-repo destroy validate fmt clean \
        e2e-init e2e-validate e2e-plan e2e-apply e2e-verify e2e-destroy

# Plan file location
PLAN_FILE := tfplan

# config_path passed to Terraform so the module can locate YAML files.
# Consumers of the published module set this in their own main.tf instead.
export TF_VAR_config_path := $(abspath config)

# Default target
help:
	@echo "GitHub Organization Terraform Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  init       Initialize Terraform (download providers)"
	@echo "  plan       Preview changes and save plan to file"
	@echo "  plan-repo  Plan for a single repository (REPO=name)"
	@echo "  plan-show  Show saved plan in human-readable format"
	@echo "  plan-pr    Run plan and post comment to GitHub PR (CI)"
	@echo "  apply      Apply changes from saved plan"
	@echo "  apply-repo Apply changes for a single repository (REPO=name)"
	@echo "  destroy    Destroy all managed resources (use with caution)"
	@echo "  validate   Validate Terraform configuration"
	@echo "  fmt        Format Terraform files"
	@echo "  clean      Remove Terraform cache, state files, and plan"
	@echo ""
	@echo "Examples:"
	@echo "  make plan-repo REPO=my-repo-name"
	@echo "  make apply-repo REPO=my-repo-name"
	@echo ""
	@echo "Environment:"
	@echo "  GITHUB_TOKEN must be set (see .env.example)"

# Initialize Terraform
init:
	@echo "Initializing Terraform..."
	terraform init

# Plan changes and save to file
plan:
	@echo "Planning Terraform changes..."
	terraform plan -out=tfplan
	@echo ""
	@echo "Plan saved to $(PLAN_FILE)"
	@echo "Run 'make plan-show' to view the plan or 'make apply' to apply"

# Plan for a single repository
plan-repo:
	@if [ -z "$(REPO)" ]; then \
		echo "Error: REPO is required. Usage: make plan-repo REPO=repository-name"; \
		exit 1; \
	fi
	@echo "Planning changes for repository: $(REPO)..."
	terraform plan -target='module.repositories["$(REPO)"]' -out=tfplan
	@echo ""
	@echo "Plan saved to $(PLAN_FILE)"
	@echo "Run 'make plan-show' to view the plan or 'make apply' to apply"

# Show saved plan in human-readable format
plan-show:
	@if [ ! -f "$(PLAN_FILE)" ]; then \
		echo "Error: No plan file found. Run 'make plan' first."; \
		exit 1; \
	fi
	terraform show tfplan

# Run plan and post comment to GitHub PR (for CI)
# Requires: GITHUB_TOKEN, TFCMT_REPO_OWNER, TFCMT_REPO_NAME, TFCMT_PR_NUMBER
plan-pr:
	@echo "Running plan with tfcmt..."
	tfcmt plan -- terraform plan

# Apply changes from saved plan
apply:
	@if [ ! -f "$(PLAN_FILE)" ]; then \
		echo "Error: No plan file found. Run 'make plan' first."; \
		exit 1; \
	fi
	@echo "Applying Terraform changes from saved plan..."
	terraform apply tfplan
	@rm -f $(PLAN_FILE)
	@echo "Plan file removed after successful apply"

# Apply changes for a single repository (without requiring saved plan)
apply-repo:
	@if [ -z "$(REPO)" ]; then \
		echo "Error: REPO is required. Usage: make apply-repo REPO=repository-name"; \
		exit 1; \
	fi
	@echo "Applying changes for repository: $(REPO)..."
	terraform apply -target='module.repositories["$(REPO)"]'

# Destroy resources (with confirmation)
destroy:
	@echo "WARNING: This will destroy all managed resources!"
	terraform destroy

# Validate configuration
validate:
	@echo "Validating Terraform configuration..."
	terraform validate

# Format Terraform files
fmt:
	@echo "Formatting Terraform files..."
	terraform fmt -recursive

# Clean up
clean:
	@echo "Cleaning up Terraform cache and plan..."
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f $(PLAN_FILE)
	@echo "Note: State files (*.tfstate) are preserved for safety"

# ── E2E test fixture targets ─────────────────────────────────────────────────
# Delegates to tests/e2e/Makefile.  Requires GITHUB_TOKEN and terraform.tfvars
# in tests/e2e/ (see tests/e2e/terraform.tfvars.example).

e2e-init:
	$(MAKE) -C tests/e2e init

e2e-validate:
	$(MAKE) -C tests/e2e validate

e2e-plan:
	$(MAKE) -C tests/e2e plan

e2e-apply:
	$(MAKE) -C tests/e2e apply

e2e-verify:
	$(MAKE) -C tests/e2e verify

e2e-destroy:
	$(MAKE) -C tests/e2e destroy
