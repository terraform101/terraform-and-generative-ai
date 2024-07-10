# --------------------------------------------------------- #
# providers.tf : Terraform에서 사용할 Provider를 설정
# --------------------------------------------------------- #

# Terraform 버전 설정
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

# AWS Provider 설정
provider "aws" {
  region = var.region

  access_key = var.access_key
  secret_key = var.secret_key

  # shared_credentials_files = ["$HOME/.aws/credentials"] # Shared Credentials 설정
  # profile                  = "work"                     # Profile 설정

  #### Assume Role 설정
  # assume_role {
  #     role_arn = "arn:aws:iam::327821849794:role/TerraformAssumedRole"
  # }

  #### Default Tags 설정
  default_tags {
    tags = {
      Environment = "Dev"
      Project     = "RAG for Bedrock"
      ManagedBy   = "Terraform"
    }
  }
}

# OpenSearch Provider 설정
provider "opensearch" {
  url         = "https://${aws_opensearch_domain.rag.endpoint}"
  aws_region  = var.region
  username    = var.domain_name
  password    = random_password.password.result
  healthcheck = false

  #### Must be disabled for basic auth
  sign_aws_requests = false
}