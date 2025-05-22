from langchain.agents import initialize_agent, Tool
import os
from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

# Initialize the model
llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash-preview-05-20", google_api_key=google_api_key)

# Ask the question
response = llm.invoke("What is the capital of France?")
print(response.content)



# Initialize the Gemini Embeddings model
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-exp-03-07",
    google_api_key=google_api_key
)

# Get embedding for a sample text
text = "Paris is the capital of France."
embedding_result = embeddings.embed_query(text)

# Print the embedding vector
print(embedding_result) 
print(len(embedding_result))