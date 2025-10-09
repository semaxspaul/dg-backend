from __future__ import annotations
import re, warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union

import numpy as np
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# ---------- File readers ----------
import docx
from PyPDF2 import PdfReader

def _read_txt(p: Union[str, Path]) -> str:
    return Path(p).read_text(encoding="utf-8", errors="ignore")

def _read_docx(p: Union[str, Path]) -> str:
    d = docx.Document(str(p))
    return "\n".join(par.text for par in d.paragraphs)

def _read_pdf(p: Union[str, Path]) -> str:
    out = []
    with open(p, "rb") as f:
        r = PdfReader(f)
        for page in r.pages:
            text = page.extract_text() or ""
            out.append(text)
    
    full_text = "\n".join(out)
    word_count = len(full_text.split())
    print(f"DEBUG: {p.name}: {len(full_text)} chars, {word_count} words")
    
    # If no text extracted, try alternative method
    if len(full_text.strip()) == 0:
        print("WARNING: No text extracted from PDF with PyPDF2 - trying alternative method")
        try:
            # Try with pdfplumber if available
            import pdfplumber
            with pdfplumber.open(p) as pdf:
                alt_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    alt_text += page_text + "\n"
                print(f"DEBUG: Alternative extraction with pdfplumber: {len(alt_text)} chars")
                if len(alt_text.strip()) > 0:
                    return alt_text
        except ImportError:
            print("DEBUG: pdfplumber not available, using PyPDF2 result")
        except Exception as e:
            print(f"DEBUG: pdfplumber failed: {e}")
        
        print("WARNING: No text could be extracted from PDF - might be image-based or scanned document")
    
    return full_text

READERS = {".txt": _read_txt, ".docx": _read_docx, ".pdf": _read_pdf}


# ---------- Simple English cleaner ----------
def basic_clean_en(text: str) -> str:
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# =========================
# Base class
# =========================
class BaseTopicModel:
    def __init__(self):
        self.docs: List[str] = []
        self.doc_names: List[str] = []

    def load_files(self, paths: List[Union[str, Path]]) -> "BaseTopicModel":
        docs, names = [], []
        for p in paths:
            p = Path(p)
            if not p.exists():
                print(f"[WARN] missing: {p}")
                continue
            reader = READERS.get(p.suffix.lower())
            if not reader:
                print(f"[WARN] unsupported: {p.suffix} ({p.name})")
                continue
            try:
                docs.append(reader(p))
                names.append(p.name)
            except Exception as e:
                print(f"[WARN] read fail {p.name}: {e}")
        self.docs, self.doc_names = docs, names
        return self

    def set_docs(self, docs: List[str], names: Optional[List[str]] = None) -> "BaseTopicModel":
        self.docs = list(docs)
        self.doc_names = names if names is not None else [f"doc_{i}" for i in range(len(docs))]
        return self

    def preprocess(self) -> "BaseTopicModel":
        self.docs = [basic_clean_en(d) for d in self.docs]
        return self

    # abstract API
    def fit(self, *a, **k): raise NotImplementedError
    def topics(self, topn: int = 15) -> List[Dict[str, float]]: raise NotImplementedError
    def document_topics(self) -> List[Dict[str, float]]: raise NotImplementedError
    def transform(self, new_docs: List[str]): raise NotImplementedError

    # shared viz
    def _plot_bar(self, words: List[str], weights: List[float], title: str):
        plt.figure(figsize=(8,4.5))
        plt.bar(words, weights)
        plt.xticks(rotation=45, ha="right")
        plt.title(title)
        plt.tight_layout()
        plt.show()

    def _plot_wc(self, freqs: Dict[str, float], title: str):
        wc = WordCloud(width=900, height=450, background_color="white").generate_from_frequencies(freqs)
        plt.figure(figsize=(10,5))
        plt.imshow(wc, interpolation="bilinear")
        plt.axis("off"); plt.title(title); plt.show()


# =========================
# 1) LDA (scikit-learn implementation)
# =========================
class LdaTopicModel(BaseTopicModel):
    def __init__(
        self,
        n_topics: int = 10,
        max_features: int = 20_000,
        min_df: Union[int, float] = 2,
        max_df: Union[int, float] = 0.95,
        ngram_range: Tuple[int,int] = (1,1),
        random_state: int = 42,
    ):
        super().__init__()
        self.n_topics = n_topics
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range
        self.random_state = random_state

        # sklearn artifacts
        self.vectorizer = None
        self.vocab: Optional[List[str]] = None
        self.doc_term_matrix = None
        self.lda = None
        self.doc_topic_matrix: Optional[np.ndarray] = None

    def fit(self, n_iter: int = 20, learning_method: str = "batch") -> "LdaTopicModel":
        from sklearn.feature_extraction.text import CountVectorizer
        from sklearn.decomposition import LatentDirichletAllocation

        if not self.docs:
            raise RuntimeError("No documents. Use set_docs(...) or load_files(...).")

        # Vectorize (English stopwords built-in)
        self.vectorizer = CountVectorizer(
            max_features=self.max_features,
            min_df=self.min_df,
            max_df=self.max_df,
            ngram_range=self.ngram_range,
            stop_words="english",
        )
        self.doc_term_matrix = self.vectorizer.fit_transform(self.docs)
        self.vocab = self.vectorizer.get_feature_names_out().tolist()

        # LDA (variational Bayes)
        self.lda = LatentDirichletAllocation(
            n_components=self.n_topics,
            random_state=self.random_state,
            learning_method=learning_method,  # 'batch' or 'online'
            max_iter=n_iter,
            n_jobs=-1,
            evaluate_every=-1,
        )
        self.doc_topic_matrix = self.lda.fit_transform(self.doc_term_matrix)
        return self

    def topics(self, topn: int = 15) -> List[Dict[str, float]]:
        if self.lda is None or self.vocab is None:
            raise RuntimeError("Fit LDA first.")
        out = []
        comps = self.lda.components_  # (K, V)
        for k in range(comps.shape[0]):
            idx = np.argsort(comps[k])[::-1][:topn]
            words = [self.vocab[i] for i in idx]
            weights = comps[k, idx]
            out.append({w: float(wt) for w, wt in zip(words, weights)})
        return out

    def document_topics(self) -> List[Dict[str, float]]:
        if self.doc_topic_matrix is None:
            raise RuntimeError("Fit LDA first.")
        return [{f"topic_{i}": float(p) for i, p in enumerate(row)} for row in self.doc_topic_matrix]

    def transform(self, new_docs: List[str]) -> np.ndarray:
        if self.vectorizer is None or self.lda is None:
            raise RuntimeError("Fit LDA first.")
        cleaned = [basic_clean_en(d) for d in new_docs]
        X = self.vectorizer.transform(cleaned)
        return self.lda.transform(X)

    # visualizations
    def plot_topic_barchart(self, topic_id: int, topn: int = 15):
        comp = self.lda.components_[topic_id]
        idx = np.argsort(comp)[::-1][:topn]
        words = [self.vocab[i] for i in idx]
        weights = comp[idx]
        self._plot_bar(words, list(weights), f"LDA Topic {topic_id} top-{topn}")

    def plot_topic_wordcloud(self, topic_id: int, max_words: int = 100):
        comp = self.lda.components_[topic_id]
        freqs = {w: comp[i] for i, w in enumerate(self.vocab)}
        # 상위 max_words만 쓰고 싶다면:
        # idx = np.argsort(comp)[::-1][:max_words]
        # freqs = {self.vocab[i]: comp[i] for i in idx}
        self._plot_wc(freqs, f"LDA Topic {topic_id} wordcloud")

    def plot_doc_topic_barchart(self, doc_index: int, topk: int = 10):
        probs = self.doc_topic_matrix[doc_index]
        idx = np.argsort(probs)[::-1][:topk]
        labels = [f"topic_{i}" for i in idx]
        self._plot_bar(labels, probs[idx], f"Document {doc_index} topic mix")


# =========================
# 2) BERTopic implementation
# =========================
class BERTopicModel(BaseTopicModel):
    def __init__(
        self,
        n_topics: Optional[int] = None,      # target reduction; None=auto
        ngram_range: Tuple[int,int] = (1,1),
        min_df: Union[int, float] = 2,
        max_df: Union[int, float] = 0.95,
        max_features: Optional[int] = 20000,
        embedding_model: Optional[object] = None,  # SentenceTransformer(..., device="cuda"/"mps")
    ):
        super().__init__()
        self.n_topics = n_topics
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.max_features = max_features
        self.embedding_model = embedding_model

        self.model = None
        self._probs: Optional[np.ndarray] = None
        self._topics_assigned: Optional[List[int]] = None

    def fit(self) -> "BERTopicModel":
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer

        if not self.docs:
            raise RuntimeError("No documents. Use set_docs(...) or load_files(...).")

        
        # Use BERTopic with parameters optimized for small datasets
        from umap import UMAP
        from hdbscan import HDBSCAN
        
        # Custom UMAP for small datasets to avoid spectral layout issues
        umap_model = UMAP(
            n_neighbors=min(3, len(self.docs) - 1),  # Ensure n_neighbors < n_documents
            n_components=min(2, len(self.docs) - 1),  # Reduce components for small datasets
            min_dist=0.0,
            metric='cosine',
            random_state=42,
            spread=1.0,
            local_connectivity=1,
            n_epochs=50,  # Reduce epochs for faster processing
            negative_sample_rate=1,
            repulsion_strength=0.1,
            # Use random initialization instead of spectral
            init='random'
        )
        
        # Custom HDBSCAN for small datasets - allow more flexible clustering
        hdbscan_model = HDBSCAN(
            min_cluster_size=2,  # HDBSCAN requires min_cluster_size >= 2
            min_samples=1,       # Minimum samples
            metric='euclidean',
            prediction_data=True,
            cluster_selection_epsilon=0.5,  # Much more flexible cluster selection
            cluster_selection_method='eom'  # Use EOM method for better small dataset handling
        )
        
        kwargs = {
            "calculate_probabilities": True,
            "verbose": True,  # Enable verbose for debugging
            "low_memory": True,
            "min_topic_size": 1,  # Allow very small topics for small datasets
            "umap_model": umap_model,
            "hdbscan_model": hdbscan_model,
            # Remove nr_topics="auto" as it causes issues with small datasets
        }
        
        # Add custom vectorizer for small datasets
        vec = CountVectorizer(
            ngram_range=getattr(self, 'ngram_range', (1, 1)),
            stop_words="english",
            min_df=1,  # Very permissive for small datasets
            max_df=1.0,  # Allow all documents
            max_features=1000,  # Reduce features for small datasets
        )
        kwargs["vectorizer_model"] = vec
            
        if hasattr(self, 'embedding_model') and self.embedding_model is not None:
            kwargs["embedding_model"] = self.embedding_model
            
        if hasattr(self, 'n_topics') and self.n_topics is not None:
            kwargs["nr_topics"] = self.n_topics

        
        self.model = BERTopic(**kwargs)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            self._topics_assigned, _ = self.model.fit_transform(self.docs)
        self._probs = self.model.probabilities_
        return self

    def topics(self, topn: int = 15) -> List[Dict[str, float]]:
        if self.model is None: raise RuntimeError("Fit BERTopic first.")
        td = self.model.get_topics()
        out = []
        for tid in sorted([t for t in td.keys() if t != -1]):
            pairs = td[tid][:topn]
            out.append({w: float(wt) for w, wt in pairs})
        return out

    def document_topics(self) -> List[Dict[str, float]]:
        if self.model is None: raise RuntimeError("Fit BERTopic first.")
        probs = self._probs
        info = self.model.get_topic_info()
        tids = [t for t in info["Topic"].tolist() if t != -1]
        if probs is None:
            # fallback: one-hot by assigned topic
            out = []
            for t in self._topics_assigned:
                row = {f"topic_{tid}": 0.0 for tid in tids}
                if t in tids: row[f"topic_{t}"] = 1.0
                out.append(row)
            return out
        probs = np.atleast_2d(probs)
        if len(tids) != probs.shape[1]:
            tids = tids[:probs.shape[1]]
        return [{f"topic_{t}": float(p) for t, p in zip(tids, row)} for row in probs]

    def transform(self, new_docs: List[str]) -> np.ndarray:
        if self.model is None: raise RuntimeError("Fit BERTopic first.")
        _, probs = self.model.transform([basic_clean_en(d) for d in new_docs])
        return np.atleast_2d(probs)

    # visualizations
    def plot_topic_barchart(self, topic_id: int, topn: int = 15):
        topic = self.model.get_topics().get(topic_id)
        if topic is None: raise ValueError(f"Topic {topic_id} not found.")
        words = [w for w,_ in topic[:topn]]
        weights = [wt for _,wt in topic[:topn]]
        self._plot_bar(words, weights, f"BERTopic {topic_id} top-{topn}")

    def plot_topic_wordcloud(self, topic_id: int, max_words: int = 100):
        topic = self.model.get_topics().get(topic_id)
        if topic is None: raise ValueError(f"Topic {topic_id} not found.")
        freqs = {w: wt for w, wt in topic[:max_words]}
        self._plot_wc(freqs, f"BERTopic {topic_id} wordcloud")

    def plot_doc_topic_barchart(self, doc_index: int, topk: int = 10):
        if self._probs is None: raise RuntimeError("Probabilities not available.")
        row = self._probs[doc_index]
        idx = np.argsort(row)[::-1][:topk]
        info = self.model.get_topic_info()
        tids = [t for t in info["Topic"].tolist() if t != -1]
        tids = tids[:len(row)]
        labels = [f"topic_{tids[i]}" for i in idx]
        self._plot_bar(labels, row[idx], f"Document {doc_index} topic mix")


# =========================
# Facade
# =========================
class TopicModeling:
    """
    Facade: pick 'lda' (scikit-learn) or 'bertopic'
    Handles method-specific parameter differences:
    - LDA: requires n_topics parameter
    - BERTopic: n_topics is optional (auto-detection available)
    """
    def __init__(self, method: str = "bertopic", **kwargs):
        self.method = method.lower()
        
        # Validate method
        if self.method not in ["lda", "bertopic"]:
            raise ValueError("method must be 'lda' or 'bertopic'")
        
        # Extract and validate parameters
        self._validate_parameters(**kwargs)
        
        # Prepare method-specific parameters
        if self.method == "lda":
            self.model = LdaTopicModel(**self._prepare_lda_params(kwargs))
        else:  # bertopic
            self.model = BERTopicModel(**self._prepare_bertopic_params(kwargs))

    def _extract_common_params(self, kwargs):
        """Extract parameters common to both methods"""
        return {
            'ngram_range': kwargs.get('ngram_range', (1, 1)),
            'min_df': kwargs.get('min_df', 2),
            'max_df': kwargs.get('max_df', 0.95),
            'max_features': kwargs.get('max_features', 20000)
        }

    def _prepare_lda_params(self, kwargs):
        """Prepare parameters specific to LDA"""
        params = self._extract_common_params(kwargs)
        params.update({
            'n_topics': kwargs.get('n_topics', 10),  # LDA requires n_topics
            'random_state': kwargs.get('random_state', 42)
        })
        return params

    def _prepare_bertopic_params(self, kwargs):
        """Prepare parameters specific to BERTopic - use minimal defaults"""
        # For BERTopic, use minimal parameters to avoid validation issues
        params = {}
        
        # Only include n_topics if explicitly provided and valid
        if 'n_topics' in kwargs and kwargs['n_topics'] is not None and kwargs['n_topics'] > 0:
            params['n_topics'] = kwargs['n_topics']
        
        # Include embedding_model if provided
        if 'embedding_model' in kwargs:
            params['embedding_model'] = kwargs['embedding_model']
            
        return params

    def _validate_parameters(self, **kwargs):
        """Validate parameters based on method"""
        if self.method == "lda":
            if 'n_topics' not in kwargs or kwargs['n_topics'] is None:
                raise ValueError("LDA requires n_topics parameter")
            if kwargs['n_topics'] < 2:
                raise ValueError("LDA requires at least 2 topics")
        
        elif self.method == "bertopic":
            # BERTopic: n_topics is optional, but if provided, must be valid
            if 'n_topics' in kwargs and kwargs['n_topics'] is not None:
                if kwargs['n_topics'] < 1:
                    raise ValueError("BERTopic n_topics must be >= 1 if specified")

    def get_model_info(self):
        """Get model information including topic count and detection method"""
        info = {
            "method": self.method,
            "n_topics": getattr(self.model, 'n_topics', None),
            "is_auto_topic_detection": self.method == "bertopic" and not hasattr(self.model, 'n_topics')
        }
        return info

    # Proxy methods - delegate to the underlying model
    def load_files(self, *a, **k): return self.model.load_files(*a, **k)
    def set_docs(self, *a, **k): return self.model.set_docs(*a, **k)
    def preprocess(self, *a, **k): return self.model.preprocess(*a, **k)
    def fit(self, *a, **k): return self.model.fit(*a, **k)
    def topics(self, *a, **k): return self.model.topics(*a, **k)
    def document_topics(self, *a, **k): return self.model.document_topics(*a, **k)
    def transform(self, *a, **k): return self.model.transform(*a, **k)
    def plot_topic_barchart(self, *a, **k): return self.model.plot_topic_barchart(*a, **k)
    def plot_topic_wordcloud(self, *a, **k): return self.model.plot_topic_wordcloud(*a, **k)
    def plot_doc_topic_barchart(self, *a, **k): return self.model.plot_doc_topic_barchart(*a, **k)
