from pinecone import Pinecone
import os
from dotenv import load_dotenv
load_dotenv()  

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(host=os.environ["PINECONE_HOST"])

class PineconeRepo:

    def upsert(self, vectors):
        index.upsert(vectors=vectors)

    def query(self, vector, pdfId, top_k=6):
        return index.query(
            vector=vector,
            top_k=top_k,
            filter={"pdfId": pdfId},
            include_metadata=True
        )
