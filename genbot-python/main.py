import streamlit as st
import base64
import os
from genai.bedrock import BedrockAPI
from langchain_community.callbacks import StreamlitCallbackHandler


# Sidebar
with st.sidebar:
    st.write("**Please provide your AWS credentials**")
    
    # AWS Access Key ID
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "")
    input_aws_access_key_id = st.text_input("AWS Access Key ID", value=aws_access_key_id)
    if input_aws_access_key_id:
        os.environ["AWS_ACCESS_KEY_ID"] = input_aws_access_key_id

    # AWS Secret Access Key
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    input_aws_secret_access_key = st.text_input("AWS Secret Access Key", 
                                                value=aws_secret_access_key, 
                                                type="password")
    if input_aws_secret_access_key:
        os.environ["AWS_SECRET_ACCESS_KEY"] = input_aws_secret_access_key

# Title
st.title("Terraform Code Generator")
st.write("This is a simple web app to generate Terraform code for AWS resources.")

# Sub header
if not os.environ["AWS_ACCESS_KEY_ID"] and not os.environ["AWS_SECRET_ACCESS_KEY"]:
    st.warning("Missing AWS Credentials. Please provide your AWS credentials.")
else:
    st.write("**Upload AWS Architecture to generate Terraform code for:**")
    uploaded_file = st.file_uploader("Choose a file", type=["jpg", "png"])

    if uploaded_file is not None:
        st.write("File uploaded successfully!")
        # Display the uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        st.write("Click the button below to generate Terraform code.")
        if st.button("Generate Terraform Code"):
            with st.spinner("Generating Terraform code..."):

                # uploaded image decode
                image_base64 = base64.b64encode(uploaded_file.read()).decode("utf-8")

                # Generate Terraform code
                bedrock = BedrockAPI()

                st_callback = StreamlitCallbackHandler(st.container())

                # invoke the model
                # response = bedrock.query_llm(image_base64)
                response = bedrock.query_llm(image_base64, callback=st_callback)

                # st.write(response)
                st.write_stream(response)
                print(f"response type :: {type(response)}")
                st.success("Terraform code generated successfully! \n\n"
                           "Click the button below to download the Terraform code.")
                
                answer = response['answer'].split('```hcl').pop().split('```')[0]
                if st.download_button("Download Terraform Code", answer, "main.tf"):
                    st.success("Terraform code downloaded successfully!")
                
                # if st.button("Download Terraform Code"):

                #     answer = response['answer'].split('```hcl').pop().split('```')[0]
                #     with open('main.tf', 'w') as f:
                #         f.write(answer)


def download_link(object_to_download, download_filename, download_link_text):
    """
    Generates a link to download the given object_to_download.

    :param object_to_download: The object to be downloaded.
    :param download_filename: The name of the file to be downloaded.
    :param download_link_text: The text to display for the download link.
    """

    if isinstance(object_to_download, bytes):
        object_to_download = object_to_download.decode("utf-8")
    b64 = base64.b64encode(object_to_download.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{download_filename}">{download_link_text}</a>'
    
    return href


