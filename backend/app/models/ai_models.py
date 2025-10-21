"""
AI Models and related data structures for the DeepCite system
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime

class ModelType(Enum):
    """Types of AI models supported"""
    GENERATION = "generation"
    EMBEDDING = "embedding"
    RERANKING = "reranking"

class ProviderType(Enum):
    """Types of AI providers supported"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"
    PERPLEXITY = "perplexity"

@dataclass
class ModelInfo:
    """Information about an AI model"""
    id: str
    name: str
    provider: str
    type: ModelType
    description: str = ""
    max_completion_tokens: Optional[int] = None
    embedding_dimension: Optional[int] = None
    supports_top_p: bool = True
    supports_streaming: bool = True
    cost_per_token: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with JSON-serializable values"""
        return {
            'id': self.id,
            'name': self.name,
            'provider': self.provider,
            'type': self.type.value,  # Convert enum to string
            'description': self.description,
            'max_completion_tokens': self.max_completion_tokens,
            'embedding_dimension': self.embedding_dimension,
            'supports_top_p': self.supports_top_p,
            'supports_streaming': self.supports_streaming,
            'cost_per_token': self.cost_per_token,
            'metadata': self.metadata
        }

@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    model_id: str
    provider: str
    max_completion_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GenerationResult:
    """Result from a text generation request"""
    text: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EmbeddingResult:
    """Result from an embedding generation request"""
    embeddings: List[List[float]]
    model: str
    success: bool = True
    error: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RerankingResult:
    """Result from a document reranking request"""
    scores: List[float]
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ChatMessage:
    """A single message in a chat conversation"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatConversation:
    """A complete chat conversation"""
    id: str
    messages: List[ChatMessage] = field(default_factory=list)
    model_config: Optional[ModelConfig] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

# Model registry with predefined models
MODEL_REGISTRY = {
    # OpenAI Models
    "gpt-5": ModelInfo(
        id="gpt-5",
        name="GPT 5",
        provider="openai",
        type=ModelType.GENERATION,
        description="Flagship model for coding, reasoning, and agentic tasks across domains",
        max_completion_tokens=4096,
        supports_streaming=True
    ),
    "gpt-5-mini": ModelInfo(
        id="gpt-5-mini",
        name="GPT 5 mini",
        provider="openai",
        type=ModelType.GENERATION,
        description="GPT-5 mini is a faster, more cost-efficient version of GPT-5.",
        max_completion_tokens=16384,
        supports_streaming=True
    ),
    "gpt-5-nano": ModelInfo(
        id="gpt-5-nano",
        name="GPT 5 Nano",
        provider="openai",
        type=ModelType.GENERATION,
        description="It's great for summarization and classification tasks",
        max_completion_tokens=4096,
        supports_streaming=True
    ),
    "sonar": ModelInfo(
        id="sonar",
        name="Sonar",
        provider="perplexity",
        type=ModelType.GENERATION,
        description="Perplexity Sonar - Real-time web search with AI answers",
        max_completion_tokens=100000,
        supports_streaming=True
    ),
    "sonar-pro": ModelInfo(
        id="sonar-pro",
        name="Sonar Pro",
        provider="perplexity",
        type=ModelType.GENERATION,
        description="Perplexity Sonar Pro - Enhanced web search with citations",
        max_completion_tokens=200000,
        supports_streaming=True
    ),
    "sonar-reasoning": ModelInfo(
        id="sonar-reasoning",
        name="Sonar Reasoning",
        provider="perplexity",
        type=ModelType.GENERATION,
        description="Perplexity Sonar Reasoning - Advanced reasoning capabilities",
        max_completion_tokens=100000,
        supports_streaming=True
    ),
    "sonar-reasoning-pro": ModelInfo(
        id="sonar-reasoning-pro",
        name="Sonar Reasoning Pro",
        provider="perplexity",
        type=ModelType.GENERATION,
        description="Perplexity Sonar Reasoning Pro - Professional reasoning model",
        max_completion_tokens=200000,
        supports_streaming=True
    ),
    "sonar-deep-research": ModelInfo(
        id="sonar-deep-research",
        name="Sonar Deep Research",
        provider="perplexity",
        type=ModelType.GENERATION,
        description="Perplexity Sonar Deep Research - Deep analysis and research",
        max_completion_tokens=500000,
        supports_streaming=True
    ),
    "text-embedding-3-large": ModelInfo(
        id="text-embedding-3-large",
        name="Text Embedding 3 Large",
        provider="openai",
        type=ModelType.EMBEDDING,
        description="Most capable embedding model",
        embedding_dimension=3072,
        supports_streaming=False
    ),
    "text-embedding-3-small": ModelInfo(
        id="text-embedding-3-small",
        name="Text Embedding 3 Small",
        provider="openai",
        type=ModelType.EMBEDDING,
        description="Smaller, faster embedding model",
        embedding_dimension=1536,
        supports_streaming=False
    ),

    # OpenRouter Models
    "openai/gpt-5": ModelInfo(
        id="openai/gpt-5",
        name="GPT-5",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="GPT-5 is OpenAI's most advanced model, offering major improvements in reasoning, code quality, and user experience. It is optimized for complex tasks that require step-by-step reasoning, instruction following, and accuracy in high-stakes use cases.",
        max_completion_tokens=400000,
        supports_streaming=True
    ),
    "openai/gpt-5-mini": ModelInfo(
        id="openai/gpt-5-mini",
        name="GPT-5 Mini",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="GPT-5 Mini is a compact version of GPT-5, designed to handle lighter-weight reasoning tasks. It provides the same instruction-following and safety-tuning benefits as GPT-5, but with reduced latency and cost.",
        max_completion_tokens=400000,
        supports_streaming=True
    ),
    "openai/gpt-5-nano": ModelInfo(
        id="openai/gpt-5-nano",
        name="GPT-5 Nano",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="GPT-5-Nano is the smallest and fastest variant in the GPT-5 system, optimized for developer tools, rapid interactions, and ultra-low latency environments.",
        max_completion_tokens=400000,
        supports_streaming=True
    ),
    "anthropic/claude-opus-4.1": ModelInfo(
        id="anthropic/claude-opus-4.1",
        name="Claude Opus 4.1",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="Claude Opus 4.1 is an updated version of Anthropic's flagship model, offering improved performance in coding, reasoning, and agentic tasks.",
        max_completion_tokens=200000,
        supports_streaming=True
    ),
    "anthropic/claude-sonnet-4": ModelInfo(
        id="anthropic/claude-sonnet-4",
        name="Claude Sonnet 4",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="Claude Sonnet 4 significantly enhances the capabilities of its predecessor, Sonnet 3.7, excelling in both coding and reasoning tasks with improved precision and controllability.",
        max_completion_tokens=1000000,
        supports_streaming=True
    ),
    "google/gemini-2.5-flash-lite": ModelInfo(
        id="google/gemini-2.5-flash-lite",
        name="Gemini 2.5 Flash Lite",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="Gemini 2.5 Flash-Lite is a lightweight reasoning model in the Gemini 2.5 family, optimized for ultra-low latency and cost efficiency.",
        max_completion_tokens=1050000,
        supports_streaming=True
    ),
    "google/gemini-2.5-flash": ModelInfo(
        id="google/gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="Gemini 2.5 Flash is Google's state-of-the-art workhorse model, specifically designed for advanced reasoning, coding, mathematics, and scientific tasks.",
        max_completion_tokens=1050000,
        supports_streaming=True
    ),
    "google/gemini-2.5-pro": ModelInfo(
        id="google/gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="openrouter",
        type=ModelType.GENERATION,
        description="Gemini 2.5 Pro is Google's state-of-the-art AI model designed for advanced reasoning, coding, mathematics, and scientific tasks.",
        max_completion_tokens=1050000,
        supports_streaming=True
    )
}

def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Get information about a specific model"""
    return MODEL_REGISTRY.get(model_id)

def get_models_by_type(model_type: ModelType) -> List[ModelInfo]:
    """Get all models of a specific type"""
    return [model for model in MODEL_REGISTRY.values() if model.type == model_type]

def get_models_by_provider(provider: str) -> List[ModelInfo]:
    """Get all models from a specific provider"""
    return [model for model in MODEL_REGISTRY.values() if model.provider == provider]

def get_generation_models() -> List[ModelInfo]:
    """Get all text generation models"""
    return get_models_by_type(ModelType.GENERATION)

def get_embedding_models() -> List[ModelInfo]:
    """Get all embedding models"""
    return get_models_by_type(ModelType.EMBEDDING)

def get_reranking_models() -> List[ModelInfo]:
    """Get all reranking models"""
    return get_models_by_type(ModelType.RERANKING)

def is_model_available(model_id: str) -> bool:
    """Check if a model is available in the registry"""
    return model_id in MODEL_REGISTRY

def add_model_to_registry(model_info: ModelInfo) -> None:
    """Add a new model to the registry"""
    MODEL_REGISTRY[model_info.id] = model_info

def remove_model_from_registry(model_id: str) -> bool:
    """Remove a model from the registry"""
    if model_id in MODEL_REGISTRY:
        del MODEL_REGISTRY[model_id]
        return True
    return False