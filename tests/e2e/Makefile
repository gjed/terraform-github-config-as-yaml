.PHONY: help init validate plan plan-show apply verify destroy clean

# config_path is set automatically to the e2e config directory
export TF_VAR_config_path := $(abspath config)

PLAN_FILE := tfplan

help:
	@echo "E2E Test Fixture — GitHub Org Terraform"
	@echo ""
	@echo "Prerequisites:"
	@echo "  GITHUB_TOKEN must be set with admin:org + repo + delete_repo scopes"
	@echo "  terraform.tfvars must exist (copy from terraform.tfvars.example)"
	@echo "  PyGithub must be installed: pip install PyGithub"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  init       Download providers and modules"
	@echo "  validate   Validate Terraform configuration (no credentials needed)"
	@echo "  plan       Preview changes"
	@echo "  plan-show  Show saved plan in human-readable format"
	@echo "  apply      Apply changes (creates real GitHub resources)"
	@echo "  verify     Run post-apply assertions via GitHub API"
	@echo "  destroy    Destroy all e2e-* resources (run after testing)"
	@echo "  clean      Remove Terraform cache and plan file"
	@echo ""
	@echo "Typical workflow:"
	@echo "  make init"
	@echo "  make plan"
	@echo "  make apply"
	@echo "  make verify"
	@echo "  make destroy"

init:
	@echo "Initializing Terraform..."
	terraform init

validate:
	@echo "Validating Terraform configuration..."
	terraform validate

plan:
	@echo "Planning Terraform changes..."
	terraform plan -out=$(PLAN_FILE)
	@echo ""
	@echo "Plan saved to $(PLAN_FILE). Run 'make apply' to apply."

plan-show:
	@if [ ! -f "$(PLAN_FILE)" ]; then \
		echo "Error: No plan file found. Run 'make plan' first."; \
		exit 1; \
	fi
	terraform show $(PLAN_FILE)

apply:
	@if [ ! -f "$(PLAN_FILE)" ]; then \
		echo "Error: No plan file found. Run 'make plan' first."; \
		exit 1; \
	fi
	@echo "Applying Terraform changes..."
	terraform apply $(PLAN_FILE)
	@rm -f $(PLAN_FILE)

verify:
	@echo "Running post-apply verification..."
	@echo "Exporting outputs to /tmp/e2e_outputs.json..."
	terraform output -json > /tmp/e2e_outputs.json
	python3 ../verify_e2e.py /tmp/e2e_outputs.json
	@rm -f /tmp/e2e_outputs.json

destroy:
	@echo "WARNING: This will destroy all e2e-* resources in your test org!"
	@echo "Press Ctrl-C within 5 seconds to abort..."
	@sleep 5
	terraform destroy

clean:
	@echo "Cleaning Terraform cache..."
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f $(PLAN_FILE)
	@echo "Note: State files are preserved for safety."
