# Terraform Cloud (HCP Terraform). Copy to backend.tf in your consumer repository.
#
# State storage, locking and encryption are handled by the service. Set the workspace's execution mode
# to "local" if the plan and apply should run on your CI runner, as the workflows in ci/ do; in remote
# execution mode the run happens in Terraform Cloud and the workflows only trigger it.
#
# Credentials: a Terraform Cloud API token in the TF_TOKEN_app_terraform_io environment variable.

terraform {
  required_version = ">= 1.0"

  cloud {
    organization = "your-tfc-org" # REPLACE

    workspaces {
      name = "github-org" # REPLACE
    }
  }
}
