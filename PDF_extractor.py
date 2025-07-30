import os
import json
import uuid
import re
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from PyPDF2 import PdfReader

# Load Google API key
load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')

# Set up Gemini model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, google_api_key=google_api_key)

# Folder with PDF question papers
folder_path = r"C:\Users\Henry\Documents\MSC project\LLM-Based Tutor\past papers"
output_path = "extracted_papers.json"

# Make sure the file exists (start with empty list)
if not os.path.exists(output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([], f)

# Extract text from a PDF file
def extract_text_from_pdf(file_path):
    text = ""
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += page.extract_text() + '\n'
    return text

# Extract first comprehension passage
def passage_extractor(text):
    prompt = PromptTemplate(
        input_variables=["text"],
        template="This is a question paper. Extract only the first comprehension passage and print it:\n\n{text}"
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"text": text})

# Extract questions following the passage
def question_extractor(text, passage):
    prompt = PromptTemplate(
        input_variables=["passage", "text"],
        template="""This is a question paper:\n\n{text}\n\n
                 Extract only the questions that follow after this comprehension passage:\n\n{passage}\n\n
                 Separate the questions using &&&. Do not generate anything, extract only."""
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"text": text, "passage": passage})

meterial_number = 1

#  Loop through PDFs
for filename in os.listdir(folder_path):
    if filename.lower().endswith(".pdf"):
        file_path = os.path.join(folder_path, filename)

        try:
            print(f" Processing: {filename}")
            content = extract_text_from_pdf(file_path)
            passage = passage_extractor(content)
            questions_text = question_extractor(content, passage)
            questions = [q.strip() for q in questions_text.split("&&&") if q.strip()]

            # Load current file
            with open(output_path, "r", encoding="utf-8") as f:
                current_data = json.load(f)

            # Append new result
            current_data.append({
                "passage": passage.strip(),
                "questions": questions
            })

            # Save back to file immediately
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=2, ensure_ascii=False)

            print(f" Done: {filename}")

        except Exception as e:
            print(f" Error processing {filename}: {e}")

print(f"\n All done! Each paper's data was saved as it was processed.")
