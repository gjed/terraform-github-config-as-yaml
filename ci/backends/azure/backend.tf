# Azure backend (Blob Storage). Copy to backend.tf in your consumer repository.
#
# The state holds secret values, so keep the storage account private and limit who can read the
# container. Locking is built in (blob leases).
#
# Credentials: in CI prefer OIDC (set use_oidc = true, or ARM_USE_OIDC=true, with azure/login) over a
# storage account key.

terraform {
  required_version = ">= 1.0"

  backend "azurerm" {
    resource_group_name  = "terraform-state-rg" # REPLACE
    storage_account_name = "yourtfstate"        # REPLACE
    container_name       = "tfstate"
    key                  = "github-org.terraform.tfstate"
  }
}
