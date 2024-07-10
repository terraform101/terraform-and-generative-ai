# --------------------------------------------------------- #
# main.tf : Terraform에서 사용할 리소스를 정의
# --------------------------------------------------------- #

# 현재 Account ID 가져오기
data "aws_caller_identity" "current" {}

# AWS OpenSearch Service 도메인 access policy 설정
data "aws_iam_policy_document" "this" {
  statement {
    effect = "Allow"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions   = ["es:*"]
    resources = ["arn:aws:es:${var.region}:${data.aws_caller_identity.current.account_id}:domain/${var.domain_name}/*"]
  }
}


# Amazon OpenSearch Service 도메인 생성
resource "aws_opensearch_domain" "rag" {
  depends_on     = [aws_secretsmanager_secret.secret]
  domain_name    = var.domain_name
  engine_version = "OpenSearch_2.5"

  # 도메인 설정
  cluster_config {
    instance_count                = 1
    instance_type                 = "t3.medium.search" #"r6g.large.search"
    warm_enabled                  = false
    multi_az_with_standby_enabled = false
    dedicated_master_enabled      = false
    zone_awareness_enabled        = false
  }

  # EBS 설정
  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 10
  }

  node_to_node_encryption { # using advanced security options 
    enabled = true
  }

  encrypt_at_rest { # using advanced security options
    enabled = true
  }

  domain_endpoint_options { # using advanced security options
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-0-2019-07"
  }

  auto_tune_options {
    desired_state       = "DISABLED"
    rollback_on_disable = "NO_ROLLBACK"
  }

  # advanced_options = {
  #   "rest.action.multi.allow_explicit_index" = "true"
  #   "plugins.security.disabled"              = "true"
  # }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true

    master_user_options {
      master_user_name     = var.domain_name
      master_user_password = aws_secretsmanager_secret_version.secret.secret_string
    }
  }

  access_policies = data.aws_iam_policy_document.this.json

  timeouts {
    create = "60m" # OpenSearch 도메인 생성 시간이 오래 걸릴 수 있어서 timeout 설정
    delete = "60m"
  }
}

# Random password 생성
resource "random_password" "password" {
  length           = 16
  special          = true
  override_special = "_%@"
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
  min_upper        = 1
}

# Secret Manager 중복 이름 방지
resource "random_pet" "random" {
  keepers = {
    # Generate a new pet name each time we switch to a new AMI id
    password = random_password.password.result
  }
}

# Secret Manager Secret 생성
resource "aws_secretsmanager_secret" "secret" {
  name = "opensearch-password-${random_pet.random.id}"
}

# Secret Manager Secret Version 생성
resource "aws_secretsmanager_secret_version" "secret" {
  secret_id     = aws_secretsmanager_secret.secret.id
  secret_string = random_password.password.result
}

# OpenSearch Service nori 패키지 설치/연결
resource "aws_opensearch_package_association" "nori" {
  domain_name = aws_opensearch_domain.rag.domain_name
  package_id  = "G240285063" # nori plugin package id for OpenSearch 2.5

  timeouts {
    create = "60m" # nori plugin 설치 시간이 오래 걸릴 수 있어서 timeout 설정
    delete = "60m"
  }
}

# OpenSearch Index 생성
resource "opensearch_index" "rag" {
  depends_on         = [aws_opensearch_domain.rag]
  name               = var.domain_name
  analysis_analyzer  = <<EOF
    {
      "my_analyzer" : {
        "char_filter" : ["html_strip"],
        "tokenizer" : "nori",
        "filter" : ["my_nori_part_of_speech"],
        "type" : "custom"
      }
    }
    EOF
  analysis_tokenizer = <<EOF
    {
      "nori" : {
        "decompound_mode" : "mixed",
        "discard_punctuation" : "true",
        "type" : "nori_tokenizer"
      }
    }
    EOF
  analysis_filter    = <<EOF
    {
      "my_nori_part_of_speech" : {
        "type" : "nori_part_of_speech",
        "stoptags" : [
          "J", "XSV", "E", "IC", "MAJ", "NNB",
          "SP", "SSC", "SSO",
          "SC", "SE", "XSN", "XSV",
          "UNA", "NA", "VCP", "VSV",
          "VX"
        ]
      }
    }
    EOF

  mappings = <<EOF
    {
      "properties": {
          "metadata": {
          "properties": {
              "source": {"type": "keyword"},
              "last_updated": {"type": "date"},
              "project": {"type": "keyword"},
              "seq_num": {"type": "long"},
              "title": {"type": "text"},
              "url": {"type": "text"}
          }
          },
          "text": {
          "analyzer": "my_analyzer",
          "search_analyzer": "my_analyzer",
          "type": "text"
          },
          "vector_field": {
          "type": "knn_vector",
          "dimension": 1024,
          "method": {
              "name": "hnsw",
              "space_type": "cosinesimil",
              "engine": "nmslib",
              "parameters": {
              "ef_construction": 512,
              "m": 16
              }
          }
          }
      }
    }
  EOF

  index_knn = true
  force_destroy = true
}

# python app의 .env 템플릿팅
resource "local_file" "python" {
  content = templatefile("${path.module}/genbot-python/.env.tpl", {
    AWS_DEFAULT_REGION    = var.region
    AWS_ACCESS_KEY_ID     = var.access_key
    AWS_SECRET_ACCESS_KEY = var.secret_key
    OPENSEARCH_URL        = "https://${aws_opensearch_domain.rag.endpoint}"
    OPENSEARCH_PASSWORD   = random_password.password.result
  })
  filename = abspath("${path.module}/genbot-python/.env")
}