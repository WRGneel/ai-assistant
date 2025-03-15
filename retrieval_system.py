"""
Retrieval system for AI Assistant.
Provides interfaces to search and retrieve relevant information from various sources.
"""
import os
import json
import re
from typing import List, Dict, Any, Optional, Union, Callable
from pathlib import Path
import math

class RetrieverBase:
    """Base class for retrieval systems"""
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant information for a query"""
        raise NotImplementedError("Subclasses must implement retrieve()")

    def add_document(self, document: Dict[str, Any]) -> bool:
        """Add a document to the retrieval system"""
        raise NotImplementedError("Subclasses must implement add_document()")


class KeywordRetriever(RetrieverBase):
    """Simple keyword-based retrieval system"""
    def __init__(self, documents: List[Dict[str, Any]] = None):
        self.documents = documents or []
        self.index = {}
        # Build index if documents are provided
        if documents:
            for doc in documents:
                self.add_document(doc)

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - split on non-alphanumeric chars and convert to lowercase"""
        return re.findall(r'\w+', text.lower())

    def add_document(self, document: Dict[str, Any]) -> bool:
        """Add document to index"""
        try:
            # Get document ID or generate one
            doc_id = document.get('id', len(self.documents))

            # Add to documents list
            document['id'] = doc_id
            self.documents.append(document)

            # Extract content based on document type
            content = ""
            if isinstance(document.get('content'), str):
                content = document['content']
            elif isinstance(document.get('content'), dict):
                # Flatten dict to string
                content = json.dumps(document['content'])
            elif isinstance(document.get('content'), list):
                # Handle list of dictionaries (e.g., from CSV)
                content = json.dumps(document['content'])

            # Tokenize and add to index
            tokens = self._tokenize(content)
            for token in tokens:
                if token not in self.index:
                    self.index[token] = {}
                self.index[token][doc_id] = self.index[token].get(doc_id, 0) + 1

            return True
        except Exception as e:
            print(f"Error adding document to index: {str(e)}")
            return False

    def _calculate_score(self, query_tokens: List[str], doc_id: int) -> float:
        """Calculate relevance score using TF-IDF-like scoring"""
        score = 0
        for token in query_tokens:
            if token in self.index and doc_id in self.index[token]:
                # Term frequency in document
                tf = self.index[token][doc_id]
                # Inverse document frequency
                idf = math.log(len(self.documents) / len(self.index[token]))
                score += tf * idf
        return score

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant documents based on keyword matching"""
        query_tokens = self._tokenize(query)

        # Calculate scores for all documents
        scores = {}
        for token in query_tokens:
            if token in self.index:
                for doc_id, count in self.index[token].items():
                    if doc_id not in scores:
                        scores[doc_id] = 0
                    scores[doc_id] += self._calculate_score([token], doc_id)

        # Sort by score and return top_k
        result_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

        # Get full documents
        results = []
        id_to_doc = {doc.get('id'): doc for doc in self.documents}

        for doc_id in result_ids:
            doc = id_to_doc.get(doc_id)
            if doc:
                # Add relevance score
                doc_copy = doc.copy()
                doc_copy['relevance_score'] = scores[doc_id]
                results.append(doc_copy)

        return results


class CombinedRetriever(RetrieverBase):
    """Combines multiple retrieval systems"""
    def __init__(self, retrievers: List[RetrieverBase] = None):
        self.retrievers = retrievers or []

    def add_retriever(self, retriever: RetrieverBase) -> None:
        """Add a retriever to the combined system"""
        self.retrievers.append(retriever)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve results from all retrievers and combine them"""
        all_results = []

        # Get results from all retrievers
        for retriever in self.retrievers:
            results = retriever.retrieve(query, top_k=top_k)
            all_results.extend(results)

        # Deduplicate results by ID
        seen_ids = set()
        unique_results = []

        for result in all_results:
            result_id = result.get('id')
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        # Sort by relevance score and return top_k
        sorted_results = sorted(unique_results,
                               key=lambda x: x.get('relevance_score', 0),
                               reverse=True)

        return sorted_results[:top_k]

    def add_document(self, document: Dict[str, Any]) -> bool:
        """Add document to all retrievers"""
        success = True
        for retriever in self.retrievers:
            if not retriever.add_document(document):
                success = False
        return success


class RetrievalContext:
    """Manages the retrieval system and provides context for the AI"""
    def __init__(self, retriever: RetrieverBase = None):
        self.retriever = retriever or KeywordRetriever()
        self.history = []

    def add_to_history(self, query: str, response: str) -> None:
        """Add a query-response pair to history"""
        self.history.append({
            "query": query,
            "response": response,
            "timestamp": os.path.getmtime(__file__)  # Just using file time for demo
        })

    def get_context_for_query(self, query: str, max_documents: int = 3) -> Dict[str, Any]:
        """Get context for a query, including relevant documents and history"""
        relevant_docs = self.retriever.retrieve(query, top_k=max_documents)

        return {
            "query": query,
            "relevant_documents": relevant_docs,
            "recent_history": self.history[-5:] if self.history else [],
            "timestamp": os.path.getmtime(__file__)
        }

    def format_for_llm(self, context: Dict[str, Any]) -> str:
        """Format context in a way suitable for the language model"""
        formatted = f"Query: {context['query']}\n\n"

        # Add relevant documents
        if context.get('relevant_documents'):
            formatted += "Relevant information:\n"
            for i, doc in enumerate(context['relevant_documents']):
                formatted += f"[Document {i+1}] "
                formatted += f"Source: {doc.get('filename', 'Unknown')}\n"

                # Format content based on type
                content = doc.get('content', '')
                if isinstance(content, str):
                    # Truncate if too long
                    if len(content) > 500:
                        content = content[:500] + "..."
                    formatted += f"Content: {content}\n"
                elif isinstance(content, (dict, list)):
                    formatted += f"Content: {json.dumps(content, indent=2)[:500]}...\n"

                formatted += "\n"

        # Add recent history if available
        if context.get('recent_history'):
            formatted += "\nRecent conversation history:\n"
            for i, item in enumerate(context['recent_history']):
                formatted += f"User: {item['query']}\n"
                formatted += f"Assistant: {item['response']}\n\n"

        return formatted