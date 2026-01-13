"""
RAG Service for HealthLink AI
Simple JSON-based knowledge retrieval (ChromaDB-free for compatibility)
Uses sentence similarity for retrieval
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from difflib import SequenceMatcher

# Singleton instance
_rag_service = None


def get_rag_service():
    """Get or create the RAG service singleton"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


class RAGService:
    """
    Simple RAG Service for healthcare knowledge retrieval
    Uses JSON storage and basic text similarity
    """
    
    def __init__(self):
        self.documents: List[Dict] = []
        self.db_path = Path(__file__).parent.parent / "data" / "knowledge_base.json"
        self._load_documents()
        
        # Load healthcare data if no documents exist
        if len(self.documents) == 0:
            self._load_healthcare_data()
            self._save_documents()
    
    def _load_documents(self):
        """Load documents from JSON file"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                print(f"Loaded {len(self.documents)} documents from {self.db_path}")
            except Exception as e:
                print(f"Error loading documents: {e}")
                self.documents = []
    
    def _save_documents(self):
        """Save documents to JSON file"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving documents: {e}")
    
    def _load_healthcare_data(self):
        """Load healthcare data from various JSON files"""
        data_dir = Path(__file__).parent.parent / "data"
        
        # Load disease symptoms dataset (41 diseases) - PRIORITY
        self._load_json_file(data_dir / "disease_symptoms.json", "diseases")
        
        # Load health content (symptoms, conditions, tips) - PRIORITY
        self._load_json_file(data_dir / "health_content.json", "health")
        
        # Load health tips
        self._load_json_file(data_dir / "health_tips.json", "health_tips")
        
        # Load FAQs
        self._load_json_file(data_dir / "faqs.json", "faqs")
        
        # Load products
        self._load_json_file(data_dir / "products.json", "products")
        
        # Load healthcare data from utils
        self._load_json_file(Path(__file__).parent / "utils" / "healthcare_data.json", "healthcare")
        
        print(f"Loaded {len(self.documents)} healthcare documents")
    
    def _load_json_file(self, file_path: Path, default_category: str):
        """Load documents from a JSON file"""
        if not file_path.exists():
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common keys
                for key in ['tips', 'faqs', 'products', 'items', 'data']:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                if not items:
                    # Flatten dict values that are lists
                    for value in data.values():
                        if isinstance(value, list):
                            items.extend(value)
                        elif isinstance(value, dict):
                            items.append(value)
            
            for i, item in enumerate(items):
                doc_id = f"{default_category}_{i}"
                
                if isinstance(item, dict):
                    # Extract content from various possible keys
                    content_keys = ['content', 'text', 'description', 'tip', 'answer', 'message']
                    content = None
                    for key in content_keys:
                        if key in item and item[key]:
                            content = str(item[key])
                            break
                    
                    if not content:
                        # Build content from available fields
                        parts = []
                        if 'question' in item:
                            parts.append(f"Q: {item['question']}")
                        if 'answer' in item:
                            parts.append(f"A: {item['answer']}")
                        if 'name' in item:
                            parts.append(f"Name: {item['name']}")
                        if 'description' in item:
                            parts.append(item['description'])
                        content = "\n".join(parts) if parts else json.dumps(item)
                    
                    category = item.get('category', item.get('type', default_category))
                else:
                    content = str(item)
                    category = default_category
                
                if content and len(content.strip()) > 5:
                    self.documents.append({
                        "id": doc_id,
                        "content": content,
                        "category": category,
                        "url": item.get('url', '') if isinstance(item, dict) else '',
                        "source": item.get('source', '') if isinstance(item, dict) else ''
                    })
                    
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity"""
        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def add_document(self, doc_id: str, content: str, category: str = "general") -> bool:
        """Add a document to the knowledge base"""
        try:
            # Check if document exists, update if so
            for doc in self.documents:
                if doc["id"] == doc_id:
                    doc["content"] = content
                    doc["category"] = category
                    self._save_documents()
                    return True
            
            # Add new document
            self.documents.append({
                "id": doc_id,
                "content": content,
                "category": category
            })
            self._save_documents()
            return True
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def query(self, query_text: str, n_results: int = 3) -> List[Dict]:
        """Query the knowledge base for relevant documents"""
        if not self.documents:
            return []
        
        # Calculate similarity for each document
        scored_docs = []
        for doc in self.documents:
            similarity = self._calculate_similarity(query_text, doc["content"])
            scored_docs.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": {
                    "category": doc.get("category", "general"),
                    "url": doc.get("url", ""),
                    "source": doc.get("source", "")
                },
                "distance": 1 - similarity  # Lower distance = more similar
            })
        
        # Sort by distance (ascending) and return top n
        scored_docs.sort(key=lambda x: x["distance"])
        return scored_docs[:n_results]
    
    def get_augmented_context(self, query: str, n_results: int = 3) -> str:
        """Get augmented context string for LLM consumption"""
        documents = self.query(query, n_results)
        
        if not documents:
            return ""
        
        context_parts = []
        for doc in documents:
            category = doc['metadata'].get('category', 'general')
            content = doc['content']
            context_parts.append(f"[{category.upper()}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_stats(self) -> Dict:
        """Get statistics about the knowledge base"""
        categories = {}
        for doc in self.documents:
            cat = doc.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_documents": len(self.documents),
            "categories": categories,
            "database_path": str(self.db_path)
        }
    
    def clear(self) -> bool:
        """Clear all documents"""
        try:
            self.documents = []
            self._save_documents()
            return True
        except Exception as e:
            print(f"Error clearing: {e}")
            return False
