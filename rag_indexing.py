from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()
import os
pinecone_api_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=pinecone_api_key)

spec = ServerlessSpec(cloud='aws', region='us-east-1')

pc.create_index(
    name="past-papers-index",
    dimension=768,
    metric="cosine",
    spec=spec  
)

indices = pc.list_indexes()
print(indices)

INDEX_NAME = "past-papers-index"

# Use raw strings (r"...") to handle backslashes in Windows paths
PDF_PATHS = [
    r"## put he specific path to the file\2008pp English FAL P1 Nov 2008.pdf",
    r"## put he specific path to the file\English FAL P1 Feb-March 2013.pdf",
    r"## put he specific path to the file\English FAL P1 Feb-March 2014.pdf",
    r"## put he specific path to the file\English FAL P1 Feb-March 2015.pdf",
    r"## put he specific path to the file\English FAL P1 May-June 2018.pdf",
    r"## put he specific path to the file\English FAL P1 May-June 2019.pdf",
    r"## put he specific path to the file\English FAL P1 May-June 2021.pdf"
]

# Load PDFs and extract FULL text per PDF
texts = []
metadatas = []

for pdf_path in PDF_PATHS:
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    full_text = " ".join(page.page_content for page in pages)

    texts.append(full_text)
    metadatas.append({
        "source": os.path.basename(pdf_path)
    })

# Embeddings must match index dimension (768)
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=768
)

####pinecone

pinecone_api_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=pinecone_api_key)

spec = ServerlessSpec(cloud='aws', region='us-east-1')

# Store each PDF as ONE document (ONE vector) with metadata
vectorstore = PineconeVectorStore.from_texts(
    texts=texts,
    embedding=embeddings,
    index_name=INDEX_NAME,
    metadatas=metadatas  # ← Added this to include metadata
)

print(f"{len(texts)} PDFs stored as individual vectors in '{INDEX_NAME}'")

