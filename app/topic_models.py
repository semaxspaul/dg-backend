"""
Topic Modeling Module for DataGround
"""

import os
import re
import json
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopicModeling:
    """
    Topic modeling class supporting LDA and BERTopic methods
    """
    
    def __init__(self, 
                 method: str = "lda",
                 n_topics: int = 10,
                 min_df: float = 2.0,
                 max_df: float = 0.95,
                 ngram_range: Tuple[int, int] = (1, 1),
                 random_state: int = 42,
                 **kwargs):
        """
        Initialize TopicModeling instance
        
        Args:
            method: Topic modeling method ('lda' or 'bertopic')
            n_topics: Number of topics (for LDA only)
            min_df: Minimum document frequency (for LDA only)
            max_df: Maximum document frequency (for LDA only)
            ngram_range: N-gram range for vectorization (for LDA only)
            random_state: Random state for reproducibility (for LDA only)
        """
        self.method = method.lower()
        self.model = None
        self.vectorizer = None
        self.topics = None
        self.documents = []
        
        # LDA-specific parameters
        if self.method == "lda":
            self.n_topics = n_topics
            self.min_df = min_df
            self.max_df = max_df
            self.ngram_range = ngram_range
            self.random_state = random_state
        # BERTopic-specific parameters (if any)
        elif self.method == "bertopic":
            # BERTopic doesn't use these parameters
            pass
        
    def fit(self, documents: List[str]) -> Dict[str, Any]:
        """
        Fit the topic model to documents
        
        Args:
            documents: List of document texts
            
        Returns:
            Dictionary containing model results
        """
        self.documents = documents
        
        if self.method == "lda":
            return self._fit_lda()
        elif self.method == "bertopic":
            return self._fit_bertopic()
        else:
            raise ValueError(f"Unsupported method: {self.method}")
    
    def _fit_lda(self) -> Dict[str, Any]:
        """Fit LDA model"""
        try:
            from sklearn.feature_extraction.text import CountVectorizer
            from sklearn.decomposition import LatentDirichletAllocation

            # Create vectorizer
            self.vectorizer = CountVectorizer(
                max_df=self.max_df,
                min_df=self.min_df,
                ngram_range=self.ngram_range,
                stop_words='english'
            )
            
            # Vectorize documents
            doc_term_matrix = self.vectorizer.fit_transform(self.documents)

            # Create LDA model
            self.model = LatentDirichletAllocation(
            n_components=self.n_topics,
            random_state=self.random_state,
                max_iter=100
            )
            
            # Fit model
            self.model.fit(doc_term_matrix)
            
            # Get topics
            feature_names = self.vectorizer.get_feature_names_out()
            self.topics = []
            
            for topic_idx, topic in enumerate(self.model.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                self.topics.append({
                    'topic_id': topic_idx,
                    'words': top_words,
                    'weights': topic[top_words_idx].tolist()
                })
            
            # Get document topics
            doc_topics = self.model.transform(doc_term_matrix)
            doc_topic_assignments = []
            
            for i, doc in enumerate(self.documents):
                topic_probs = doc_topics[i]
                dominant_topic = topic_probs.argmax()
                doc_topic_assignments.append({
                    'document': doc[:100] + "..." if len(doc) > 100 else doc,
                    'dominant_topic': int(dominant_topic),
                    'topic_probability': float(topic_probs[dominant_topic])
                })
            
            return {
                'method': 'lda',
                'n_topics': self.n_topics,
                'topics': self.topics,
                'document_assignments': doc_topic_assignments,
                'model_info': {
                    'n_topics': self.n_topics,
                    'is_auto_topic_detection': False,
                    'n_documents': len(self.documents),
                    'vocabulary_size': len(feature_names),
                    'perplexity': self.model.perplexity(doc_term_matrix)
                }
            }
            
        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            raise HTTPException(status_code=500, detail="Required packages not installed for LDA topic modeling")
    
    def _fit_bertopic(self) -> Dict[str, Any]:
        """Fit BERTopic model - automatically determines number of topics"""
        try:
            from bertopic import BERTopic
            from umap import UMAP
            
            # Create UMAP with adjusted parameters for small datasets
            n_docs = len(self.documents)
            umap_model = UMAP(
                n_neighbors=min(15, max(2, n_docs - 1)),  # Adjust for small datasets
                n_components=2,
                min_dist=0.0,
                metric='cosine',
                random_state=42
            )
            
            # Create BERTopic model (auto-detects number of topics)
            self.model = BERTopic(
                min_topic_size=2,  # Minimum documents per topic
                umap_model=umap_model
            )
            
            # Fit model
            topics, probs = self.model.fit_transform(self.documents)
            
            # Get topic information
            topic_info = self.model.get_topic_info()
            self.topics = []
            
            for _, row in topic_info.iterrows():
                if row['Topic'] != -1:  # Exclude outlier topic
                    topic_words = self.model.get_topic(row['Topic'])
                    self.topics.append({
                        'topic_id': int(row['Topic']),
                        'words': [word for word, _ in topic_words],
                        'weights': [weight for _, weight in topic_words],
                        'count': int(row['Count'])
                    })
            
            # Get document topics
            doc_topic_assignments = []
            for i, doc in enumerate(self.documents):
                # Handle probability calculation safely
                if probs is not None and len(probs) > i:
                    if hasattr(probs[i], '__len__') and len(probs[i]) > topics[i]:
                        topic_prob = float(probs[i][topics[i]])
                    else:
                        topic_prob = 1.0
                else:
                    topic_prob = 1.0
                
                doc_topic_assignments.append({
                    'document': doc[:100] + "..." if len(doc) > 100 else doc,
                    'dominant_topic': int(topics[i]),
                    'topic_probability': topic_prob
                })
            
            return {
                'method': 'bertopic',
                'n_topics': len(self.topics),
                'topics': self.topics,
                'document_assignments': doc_topic_assignments,
                'model_info': {
                    'n_topics': len(self.topics),
                    'is_auto_topic_detection': True,
                    'n_documents': len(self.documents),
                    'n_topics_found': len(self.topics)
                }
            }
            
        except ImportError as e:
            logger.error(f"Required packages not installed: {e}")
            raise HTTPException(status_code=500, detail="Required packages not installed for BERTopic modeling")
    
    def get_topics(self) -> List[Dict[str, Any]]:
        """Get discovered topics"""
        return self.topics or []
    
    def get_document_topics(self) -> List[Dict[str, Any]]:
        """Get document topic assignments"""
        if not self.model:
            return []
        
        if self.method == "lda":
            doc_term_matrix = self.vectorizer.transform(self.documents)
            doc_topics = self.model.transform(doc_term_matrix)
            
            assignments = []
            for i, doc in enumerate(self.documents):
                topic_probs = doc_topics[i]
                dominant_topic = topic_probs.argmax()
                assignments.append({
                    'document': doc[:100] + "..." if len(doc) > 100 else doc,
                    'dominant_topic': int(dominant_topic),
                    'topic_probability': float(topic_probs[dominant_topic])
                })
            return assignments
        
        elif self.method == "bertopic":
            topics, probs = self.model.transform(self.documents)
            assignments = []
            for i, doc in enumerate(self.documents):
                # Handle probability calculation safely
                if probs is not None and len(probs) > i:
                    if hasattr(probs[i], '__len__') and len(probs[i]) > topics[i]:
                        topic_prob = float(probs[i][topics[i]])
                    else:
                        topic_prob = 1.0
                else:
                    topic_prob = 1.0
                
                assignments.append({
                    'document': doc[:100] + "..." if len(doc) > 100 else doc,
                    'dominant_topic': int(topics[i]),
                    'topic_probability': topic_prob
                })
            return assignments
        
        return []


# File readers for different document types
def read_txt(file_path: Path) -> str:
    """Read text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()

def read_docx(file_path: Path) -> str:
    """Read DOCX file"""
    try:
        from docx import Document
        doc = Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    except ImportError:
        raise ImportError("python-docx package required for DOCX files")

def read_pdf(file_path: Path) -> str:
    """Read PDF file"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
    except ImportError:
        raise ImportError("PyPDF2 package required for PDF files")

# Dictionary of file readers
READERS = {
    '.txt': read_txt,
    '.docx': read_docx,
    '.pdf': read_pdf
}
