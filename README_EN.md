# Terraform with Gen AI

> The result is output in Korean due to a predeclared prompt. If you want to modify it, please check `human_prompt` in `genai/bedrock.py`.

## 1. Bedrock and Open Search

Describes how to set up and provision an Amazon OpenSearch Service domain using Terraform code. This file is a guide for users who are unfamiliar with AWS, OpenSearch, and Terraform.

### Requirements

- Installed Terraform CLI
- Set up your AWS account and credentials
- Install and configure the AWS CLI

### File structure

- `main.tf`: Files that define the resources to be used by Terraform

### Terraform code description

#### Get the current AWS Account ID

```hcl
data "aws_caller_identity" "current" {}
```

- Get the ID of the current AWS account.

#### Setting up AWS OpenSearch Service domain access policies

```hcl
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
```

- Set access permissions for the OpenSearch domain.

#### Create an Amazon OpenSearch Service domain

```hcl
resource "aws_opensearch_domain" "rag" {
  depends_on     = [aws_secretsmanager_secret.secret]
  domain_name    = var.domain_name
  engine_version = "OpenSearch_2.13"
  ...
}
```

- Create an OpenSearch domain.
- Set up cluster configuration, EBS options, node-to-node encryption, REST encryption, domain endpoint options, and more.
- Enable the internal user database with the Advanced Security option, and set a master username and password.
- Apply the access policy.

#### Generate a random password

```hcl
resource "random_password" "password" {
  length           = 16
  special          = true
  override_special = "_%@"
  min_lower        = 1
  min_numeric      = 1
  min_special      = 1
  min_upper        = 1
}
```

- Generate a random password to use as the OpenSearch master user password.

#### Create and version AWS Secrets Manager secrets

```hcl
resource "aws_secretsmanager_secret" "secret" {
  name = "opensearch-password"
}

resource "aws_secretsmanager_secret_version" "secret" {
  secret_id     = aws_secretsmanager_secret.secret.id
  secret_string = random_password.password.result
}
```

- Secrets Manager securely stores OpenSearch passwords.

#### Installing/connecting the OpenSearch Service `nori` package

```hcl
resource "aws_opensearch_package_association" "nori" {
  domain_name = aws_opensearch_domain.rag.domain_name
  package_id  = "G225840180"
  ...
}
```

- Install and connect the nori package to your OpenSearch domain.

#### Create an OpenSearch index

```hcl
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
}
```

- Create an OpenSearch index and configure analysers, torquers, filters, and mapping settings.

### How to apply Terraform

1. **Setting variables**:

   - Create a `variables.tf` file to define the variables you need.

   - Example:

    ```hcl
    variable "region" {
      description = "The AWS region to deploy to"
      type        = string
      default     = "us-east-1"
    }

    variable "domain_name" {
      description = "The name of the OpenSearch domain"
      type        = string
      default     = "rag"
    }
    ```

2. **Terraform initialize**:

  ```sh
  terraform init
  ```

3. **Checking a Terraform plan**:

  ```sh
  terraform plan
  ```

4. **Applying Terraform**:

  ```sh
  terraform apply
  ```

### What to watch out for

- Creating an OpenSearch domain and installing packages can take some time. This has been prepared for by setting `timeouts`.
- Make sure the permissions on your AWS account are set correctly.
- Some other `Secrets Management` system helps you manage your passwords securely.


## 2. GenAI Python Sample

![Sample](./genbot-python/images/sample.png)

### Requirements

- AWS accounts and credentials
- Install and configure the AWS CLI
- Enabling models in Bedrock
  - Titan Text Embeddings V2
  - Claude 3.5 Sonnet
- Install Python 3.8 or later (depending on the version specified in the `Pipfile`)
- Install the required Python packages (using `Pipenv`)

### File structure

- `main.py`: Main file to run a web application using Streamlit
- `genai/bedrock.py`: File containing logic to generate Terraform code using AWS Bedrock and OpenSearch, with leading prompts
- `Pipfile`: List of required packages and Python version requirements

### Key features

This application generates Terraform code based on AWS architecture image files that you upload. It leverages AWS Bedrock and OpenSearch services to analyse the image, identify the required Terraform modules, and generate the code.

### Key technologies used

#### Streamlit

`Streamlit` is an open source Python library for quickly building data applications. It empowers data scientists and engineers to create interactive web applications using simple Python scripts.

#### AWS Bedrock

`AWS Bedrock` is a service that makes it easy to build, deploy, and manage AI and machine learning applications. Developers can quickly develop AI applications using pre-built models and frameworks. Bedrock provides a comprehensive platform to manage every step of the machine learning workflow.

#### Amazon OpenSearch Service

`Amazon OpenSearch` Service is a scalable, open source search and analytics engine. It is used for log analytics, real-time application monitoring, building search applications, and more. As an AWS managed service, you can easily manage cluster operations, scaling, security settings, and more.

### How to use the application

1. **Set up AWS credentials**:
  - Before running `main.py`, you need to set up your AWS credentials.
  - Set your AWS Access Key ID and Secret Access Key in the `.env` file or enter them from the Streamlit sidebar.

2. **Install the required packages**:
  - In a terminal, run `pip install pipenv` or `pip3 install pipenv` to install the required packages.
  - Run the `pipenv install` command in the terminal to install the required packages.
  - Activate the virtual environment using the `pipenv shell` command.

3. **Run the application**:
  - Start the application by running the `streamlit run main.py` command in the terminal.
  - You can view the application by connecting to the localhost address in a web browser.

4. **Upload an AWS architecture image**:
  - Upload the AWS architecture image file from the application interface.
  - Supported file formats are JPG and PNG.

5. **Generate Terraform code**:
  - After uploading the image, click the `Generate Terraform Code` button to generate the Terraform code.
  - The generated code is displayed on the screen and can be saved as a `main.tf` file via the Download button.

### Code description

#### `main.py`

The `main.py` file uses Streamlit to run the web application. In the sidebar, enter your AWS credentials, upload an image, and generate Terraform code.

#### `genai/bedrock.py`

The `bedrock.py` file contains the logic to analyse the image and generate Terraform code using AWS Bedrock and OpenSearch.

- The `BedrockAPI` class initialises the Bedrock client and sets the LLM model and embedding model.
- The `query_llm` method generates Terraform code using Bedrock LLM based on the uploaded image.

### What to watch out for

- Manage your AWS credentials securely. We recommend storing them in an `.env` file or setting an environment variable.
- OpenSearch and Bedrock services can incur AWS charges, so be careful when using them.
- If you encounter issues while using your application, you can debug them by checking the terminal logs.

### App launch/request flow

```mermaid
graph TD
  A[main.py start] --> B[Create Sidebar]
  B --> C[Enter AWS credentials from user]
  
  C --> E{Check for AWS credentials}
  E -->|None| F[Display warning message]
  E -->|Exist| G[Allow file upload]
  G --> H[Display image and "Generate Terraform code" button upon successful upload]
  H --> I[Start generating code when button is clicked]
  
  I --> J[Decode uploaded image]
  J --> K[Create BedrockAPI object]
  K --> L[Create StreamlitCallbackHandler object]
  L --> M[Call BedrockAPI.query_llm]
  
  M --> N[Start bedrock.py]
  N --> O[Initialize BedrockAPI]
  O --> P[Create boto3 client]
  
  P --> Q[Call BedrockAPI.get_llm]
  Q --> R[Create ChatBedrock]
  Q --> S[Call BedrockAPI.get_embeddings]
  S --> T[Create BedrockEmbeddings and load JSON data]
  T --> U[Create OpenSearchVectorSearch]
  
  U --> V[Perform query_llm]
  V --> W[Set System and Human prompts]
  W --> X[Create LLMChain and QAWithSourcesChain]
  X --> Y[Perform query and receive response]
  Y --> Z[Return response and complete Terraform code generation]

  I --> AA[Display Terraform code generation complete message]
  AA --> AB[Display Terraform code download button]
  AB --> AC[Download Terraform code]
  
  click B href "https://docs.streamlit.io/en/stable/"
  click P href "https://boto3.amazonaws.com/v1/documentation/api/latest/index.html"
  click R href "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html"
  click T href "https://opensearch.org/"
  click W href "https://langchain.readthedocs.io/en/latest/"
  click X href "https://python.langchain.com/en/latest/"
```