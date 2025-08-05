import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.document_loaders.word_document import Docx2txtLoader
import json

class RAGSystem:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.vector_store = None
        self.documents = []
        
    def load_document(self, file_path):
        if file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError("Unsupported file format")
            
        documents = loader.load()
        return self.text_splitter.split_documents(documents)
    
    def process_document(self, file_path, doc_id):
        # Load and split document
        chunks = self.load_document(file_path)
        
        # Create embeddings
        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.model.encode(texts)
        
        # Initialize or update FAISS index
        if self.vector_store is None:
            dimension = embeddings.shape[1]
            self.vector_store = faiss.IndexFlatL2(dimension)
            
        # Add vectors to index
        self.vector_store.add(embeddings.astype('float32'))
        
        # Store document chunks
        for i, chunk in enumerate(chunks):
            self.documents.append({
                'id': f"{doc_id}_{i}",
                'content': chunk.page_content,
                'metadata': chunk.metadata
            })
            
        # Save vector store and documents
        self._save_state()
        
    def query(self, query_text, k=3):
        if self.vector_store is None:
            return []
            
        # Get query embedding
        query_embedding = self.model.encode([query_text])[0]
        
        # Search in vector store
        distances, indices = self.vector_store.search(
            query_embedding.reshape(1, -1).astype('float32'), k
        )
        
        # Return relevant documents
        results = []
        for idx in indices[0]:
            if idx < len(self.documents):
                results.append(self.documents[idx])
                
        return results
    
    def _save_state(self):
        # Save vector store
        if self.vector_store is not None:
            faiss.write_index(self.vector_store, 'vector_store/index.faiss')
            
        # Save documents
        with open('vector_store/documents.json', 'w') as f:
            json.dump(self.documents, f)
            
    def load_state(self):
        # Load vector store
        if os.path.exists('vector_store/index.faiss'):
            self.vector_store = faiss.read_index('vector_store/index.faiss')
            
        # Load documents
        if os.path.exists('vector_store/documents.json'):
            with open('vector_store/documents.json', 'r') as f:
                self.documents = json.load(f) 