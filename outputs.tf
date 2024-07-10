# --------------------------------------------------------- #
# outputs.tf 파일 : Terraform에서 생성한 리소스의 정보를 출력
# --------------------------------------------------------- #


# OpenSearch Domain의 엔드포인트를 출력
output "opensearch_endpoint" {
  value = aws_opensearch_domain.rag.endpoint
}

# OpenSearch Domain의 Dashboard URL을 출력
output "opensearch_dashboard" {
  value = "https://${aws_opensearch_domain.rag.dashboard_endpoint}"
}

# OpenSearch ID/Password
output "opensearch_id_password" {
  value = "${var.domain_name} / ${nonsensitive(random_password.password.result)}"
}