import os
import boto3
import base64
import json
from dotenv import load_dotenv
from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveJsonSplitter
from langchain.indexes import VectorstoreIndexCreator
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.chains.qa_with_sources.retrieval import RetrievalQAWithSourcesChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain

load_dotenv()
# 테라폼 모듈정보가 있는 terraform_moudles.json 파일을 읽어서, 테라폼 모듈 정보를 가져와 벡터스토어에 저장
# 이미지를 읽고, 이미지를 요약 해서, 어떤 리소스를 쓰고 있는지를 요약해서
# 요약된 내용을 바탕 으로 관련 모듈이 있는 지를 벡터 스토어에서 검색
# 검색된 내용을 바탕 으로 Terraform 코드를 생성
# 생성된 Terraform 코드를 리턴


class BedrockAPI:

    # Initialize Bedrock client and runtime with boto3
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name="us-east-1",
            # region_name=os.getenv("AWS_DEFAULT_REGION"),
            aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
        )

    # get llm model of the Bedrock class
    def get_llm(self):
        llm = ChatBedrock(
            client=self.client,
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",  # Bedrock LLM 모델 ID 설정
            model_kwargs={
                "max_tokens": 4096,
                "temperature": 1.0 #0.7,
                # "top_p": 0.9,
                # "top_k": 0
            },
            streaming=True,
            callbacks= [StreamingStdOutCallbackHandler()]
        )

        return llm

    def get_llm(self, callback=None):
        llm = ChatBedrock(
            client=self.client,
            model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",  # Bedrock LLM 모델 ID 설정
            model_kwargs={
                "max_tokens": 4096,
                "temperature": 1.0 #0.7,
                # "top_p": 0.9,
                # "top_k": 0
            },
            streaming=True,
            callbacks= [callback]
        )

        return llm

    # get embeddings model of the Bedrock class
    def get_embeddings(self):
        embeddings = BedrockEmbeddings(
            client        = self.client,
            model_id      = "amazon.titan-embed-text-v2:0", # Bedrock Embeddings 모델 ID 설정
        )
        
        file_path = "./data/terraform_modules.json"

        # JSONLoader를 사용하여 JSON 파일을 로드합니다.
        json_loader = JSONLoader(file_path=file_path, jq_schema=".TerraformAWSModules[]", text_content=False)
        json_data = json.load(open(file_path, "r"))
        
        json_splitter = RecursiveJsonSplitter(max_chunk_size=100)

        # JSON 데이터를 재귀적으로 분할합니다. 작은 JSON 조각에 접근하거나 조작해야 하는 경우에 사용합니다.
        json_chunks = json_splitter.split_json(json_data=json_data)

        # splitter.create_documents()를 사용하여 문서를 만들 수도 있습니다.
        docs = json_splitter.create_documents(texts=[json_data])

        # 또는 문자열 목록을 만들 수도 있습니다.
        texts = json_splitter.split_text(json_data=json_data)

        print("======================================================")

        vector_store = OpenSearchVectorSearch.from_documents(
            embedding=embeddings, # 임베딩 모델 설정
            documents=docs,
            index_name="rag", # 인덱스 이름 설정
            bulk_size= 1000, # 벌크 사이즈 설정
            opensearch_url= os.getenv("OPENSEARCH_URL"),
            http_auth= ("rag", os.getenv("OPENSEARCH_PASSWORD"))
        )

        return vector_store

    # llm에 질의하기
    def query_llm(self, image_base64, callback=None):
        #
        llm = self.get_llm(callback)

        #
        vector_store = self.get_embeddings()

        # Define system prompt
        system_prompt = ("You are a helpful assistant that generates Terraform code for AWS resources."
                         "Generate Terraform code for the following AWS resources.")
        system_prompt_template = SystemMessagePromptTemplate.from_template(system_prompt)

        # Define human prompt
        human_prompt = [
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64," + "{image_base64}",
                }

            },
            {
                "type": "text",
                "text": '''
                        Here is the contexts as texts: <contexts>{contexts}</contexts>
                '''
            },
            {
                "type": "text",
                "text": '''
                        Here is the question: 
                        
                        <question>{question}</question>

                        Follow contexts of terraform modules. Otherwise, use resource block.
                        Follow security best practices by using IAM roles and least privilege permissions.
                        Include all necessary parameters, with default values.
                        Add comments explaining the overall architecture and the purpose of each resource in Korean.                    
                        '''
            }
        ]

        human_prompt_template = HumanMessagePromptTemplate.from_template(human_prompt)

        prompt_template = ChatPromptTemplate.from_messages(
            [
                system_prompt_template,
                human_prompt_template
            ]
        )

        output_parser = StrOutputParser()
        # chain = prompt_template | llm | output_parser
        llm_chain = LLMChain(prompt=prompt_template, llm=llm, verbose=True)

        combine_documents_chain = StuffDocumentsChain(
            llm_chain=llm_chain,
            document_variable_name="contexts",
            verbose=True
        )

        qa_chain = RetrievalQAWithSourcesChain(
            retriever=vector_store.as_retriever(),
            combine_documents_chain=combine_documents_chain,
            return_source_documents=False,

        )

        response = qa_chain(
            {
                "image_base64": image_base64,
                "question": "Generate Terraform configurations for AWS services."
            }
        )
        print(response)

        return response



# Convert image to base64
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    return image_base64


if __name__ == "__main__":
    bedrock = BedrockAPI()
    llm = bedrock.get_llm()

    file_path = "./data/terraform_modules.json"

    vector_store = bedrock.get_embeddings()

    image_path = "./images/3tier-architecture.png"