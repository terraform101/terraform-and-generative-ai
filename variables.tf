# --------------------------------------------------------- #
# variables.tf 파일 : Terraform에서 사용할 변수를 정의
# --------------------------------------------------------- #

# region name 설정
variable "region" {
  description = "The AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

# opensearch domain name
variable "domain_name" {
  description = "The name of the OpenSearch domain"
  type        = string
  default     = "rag"
}

# AWS Access Key
variable "access_key" {
  type = string
}

variable "secret_key" {
  type      = string
  sensitive = true
}