# GCS backend (Google Cloud). Copy to backend.tf in your consumer repository.
#
# The state holds secret values, so keep the bucket private with uniform bucket-level access and
# object versioning, and limit who can read it. Locking is built in.
#
# Credentials: Application Default Credentials. In CI prefer Workload Identity Federation
# (google-github-actions/auth) over a service account key file.

terraform {
  required_version = ">= 1.0"

  backend "gcs" {
    bucket = "your-terraform-state-bucket" # REPLACE
    prefix = "github-org"
  }
}
