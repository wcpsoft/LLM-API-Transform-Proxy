"""
API Key Selector with pluggable strategies for intelligent key selection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Protocol
from enum import Enum
import time
import random
import threading
from src.utils.logging import logger


@dataclass
class ApiKey:
    """API Key data model with statistics."""
    id: str
    provider: str
    key: str
    auth_header: str = "Authorization"
    auth_format: str = "Bearer {key}"
    enabled: bool = True
    rate_limit: Optional[int] = None
    
    # Statistics
    requests_count: int = 0
    success_count: int = 0
    error_count: int = 0
    last_request_time: Optional[float] = None
    rate_limited_until: Optional[float] = None
    
    # Enhanced metrics
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    avg_latency: float = 0.0
    cost: float = 0.0
    last_error: Optional[str] = None
    consecutive_errors: int = 0
    last_rotation: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.requests_count == 0:
            return 1.0  # New keys get benefit of doubt
        return self.success_count / self.requests_count
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if key is currently rate limited."""
        if self.rate_limited_until is None:
            return False
        return time.time() < self.rate_limited_until
    
    @property
    def is_available(self) -> bool:
        """Check if key is available for use."""
        return self.enabled and not self.is_rate_limited
        
    @property
    def avg_tokens_per_request(self) -> float:
        """Calculate average tokens per request."""
        if self.requests_count == 0:
            return 0.0
        return self.total_tokens / self.requests_count
        
    @property
    def avg_cost_per_request(self) -> float:
        """Calculate average cost per request."""
        if self.requests_count == 0:
            return 0.0
        return self.cost / self.requests_count
        
    @property
    def needs_rotation(self) -> bool:
        """Determine if key needs rotation based on usage patterns."""
        # Rotation criteria:
        # 1. High error rate (>20% errors)
        # 2. Consecutive errors (>3)
        # 3. High usage (>10000 requests since last rotation)
        # 4. Time-based (>7 days since last rotation)
        
        if self.consecutive_errors >= 3:
            return True
            
        if self.requests_count > 0 and (self.error_count / self.requests_count) > 0.2:
            return True
            
        if self.last_rotation is not None:
            requests_since_rotation = self.requests_count - getattr(self, 'requests_at_last_rotation', 0)
            if requests_since_rotation > 10000:
                return True
                
            # Check if more than 7 days since last rotation
            if (time.time() - self.last_rotation) > (7 * 24 * 60 * 60):
                return True
                
        return False


@dataclass
class RequestContext:
    """Context information for API key selection."""
    provider: str
    model: Optional[str] = None
    request_type: str = "chat_completion"
    priority: int = 0
    user_id: Optional[str] = None
    request_size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelectionStrategy(Enum):
    """Available key selection strategies."""
    ROUND_ROBIN = "round_robin"
    SUCCESS_RATE = "success_rate"
    LEAST_USED = "least_used"
    WEIGHTED_RANDOM = "weighted_random"
    HYBRID = "hybrid"


class KeySelectionStrategy(ABC):
    """Abstract base class for key selection strategies."""
    
    @abstractmethod
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """
        Select the best key from available keys.
        
        Args:
            keys: List of available API keys
            context: Request context for selection
            
        Returns:
            Selected API key or None if no suitable key found
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass


class RoundRobinStrategy(KeySelectionStrategy):
    """Round-robin key selection strategy."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._lock = threading.Lock()
    
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """Select key using round-robin algorithm."""
        if not keys:
            return None
        
        with self._lock:
            provider_key = f"{context.provider}_{context.model or 'default'}"
            current_index = self._counters.get(provider_key, 0)
            
            # Find next available key starting from current index
            for i in range(len(keys)):
                key_index = (current_index + i) % len(keys)
                key = keys[key_index]
                
                if key.is_available:
                    self._counters[provider_key] = (key_index + 1) % len(keys)
                    return key
            
            return None
    
    def get_strategy_name(self) -> str:
        return "round_robin"


class SuccessRateStrategy(KeySelectionStrategy):
    """Success rate based key selection strategy."""
    
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """Select key with highest success rate."""
        available_keys = [key for key in keys if key.is_available]
        if not available_keys:
            return None
        
        # Sort by success rate (descending), then by least used (ascending)
        available_keys.sort(
            key=lambda k: (-k.success_rate, k.requests_count)
        )
        
        return available_keys[0]
    
    def get_strategy_name(self) -> str:
        return "success_rate"


class LeastUsedStrategy(KeySelectionStrategy):
    """Least used key selection strategy."""
    
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """Select least used key."""
        available_keys = [key for key in keys if key.is_available]
        if not available_keys:
            return None
        
        # Sort by request count (ascending), then by success rate (descending)
        available_keys.sort(
            key=lambda k: (k.requests_count, -k.success_rate)
        )
        
        return available_keys[0]
    
    def get_strategy_name(self) -> str:
        return "least_used"


class WeightedRandomStrategy(KeySelectionStrategy):
    """Weighted random key selection strategy based on success rate."""
    
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """Select key using weighted random based on success rate."""
        available_keys = [key for key in keys if key.is_available]
        if not available_keys:
            return None
        
        # Calculate weights based on success rate
        weights = []
        for key in available_keys:
            # Weight = success_rate * (1 / (requests_count + 1))
            # This gives preference to high success rate and less used keys
            weight = key.success_rate * (1.0 / (key.requests_count + 1))
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(available_keys)
        
        random_value = random.uniform(0, total_weight)
        cumulative_weight = 0
        
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if random_value <= cumulative_weight:
                return available_keys[i]
        
        return available_keys[-1]  # Fallback
    
    def get_strategy_name(self) -> str:
        return "weighted_random"


class HybridStrategy(KeySelectionStrategy):
    """Hybrid strategy that combines multiple approaches."""
    
    def __init__(self):
        self._round_robin = RoundRobinStrategy()
        self._success_rate = SuccessRateStrategy()
        self._least_used = LeastUsedStrategy()
    
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """Select key using hybrid approach."""
        available_keys = [key for key in keys if key.is_available]
        if not available_keys:
            return None
        
        # For high priority requests, use success rate strategy
        if context.priority > 5:
            return self._success_rate.select_key(keys, context)
        
        # For new keys (low usage), use least used strategy
        avg_requests = sum(k.requests_count for k in available_keys) / len(available_keys)
        if avg_requests < 10:
            return self._least_used.select_key(keys, context)
        
        # Otherwise, use round-robin for fair distribution
        return self._round_robin.select_key(keys, context)
    
    def get_strategy_name(self) -> str:
        return "hybrid"


class ApiKeySelector:
    """API Key selector with pluggable strategies."""
    
    def __init__(self, default_strategy: SelectionStrategy = SelectionStrategy.HYBRID):
        self._strategies: Dict[str, KeySelectionStrategy] = {
            SelectionStrategy.ROUND_ROBIN.value: RoundRobinStrategy(),
            SelectionStrategy.SUCCESS_RATE.value: SuccessRateStrategy(),
            SelectionStrategy.LEAST_USED.value: LeastUsedStrategy(),
            SelectionStrategy.WEIGHTED_RANDOM.value: WeightedRandomStrategy(),
            SelectionStrategy.HYBRID.value: HybridStrategy(),
        }
        self._default_strategy = default_strategy
        self._provider_strategies: Dict[str, SelectionStrategy] = {}
        self._lock = threading.Lock()
    
    def register_strategy(self, name: str, strategy: KeySelectionStrategy) -> None:
        """Register a custom selection strategy."""
        with self._lock:
            self._strategies[name] = strategy
    
    def set_provider_strategy(self, provider: str, strategy: SelectionStrategy) -> None:
        """Set specific strategy for a provider."""
        with self._lock:
            self._provider_strategies[provider] = strategy
    
    def get_strategy_for_provider(self, provider: str) -> SelectionStrategy:
        """Get the strategy configured for a provider."""
        return self._provider_strategies.get(provider, self._default_strategy)
    
    def select_key(self, keys: List[ApiKey], context: RequestContext) -> Optional[ApiKey]:
        """
        Select the best API key for the given context.
        
        Args:
            keys: List of available API keys
            context: Request context
            
        Returns:
            Selected API key or None if no suitable key found
        """
        if not keys:
            logger.warning(f"No API keys available for provider: {context.provider}")
            return None
        
        # Filter keys for the specific provider
        provider_keys = [key for key in keys if key.provider == context.provider]
        if not provider_keys:
            logger.warning(f"No API keys found for provider: {context.provider}")
            return None
        
        # Get strategy for this provider
        strategy_type = self.get_strategy_for_provider(context.provider)
        strategy = self._strategies.get(strategy_type.value)
        
        if not strategy:
            logger.error(f"Strategy not found: {strategy_type.value}")
            strategy = self._strategies[SelectionStrategy.HYBRID.value]
        
        try:
            selected_key = strategy.select_key(provider_keys, context)
            
            if selected_key:
                logger.debug(
                    f"Selected API key for {context.provider} using {strategy.get_strategy_name()}: "
                    f"key_id={selected_key.id}, success_rate={selected_key.success_rate:.2f}, "
                    f"requests={selected_key.requests_count}"
                )
            else:
                logger.warning(f"No available API key found for provider: {context.provider}")
            
            return selected_key
            
        except Exception as e:
            logger.error(f"Error selecting API key: {e}")
            # Fallback to first available key
            available_keys = [key for key in provider_keys if key.is_available]
            return available_keys[0] if available_keys else None
    
    def update_key_stats(self, key: ApiKey, success: bool, status_code: Optional[int] = None, 
                       response_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Update key statistics after a request.
        
        Args:
            key: API key to update
            success: Whether the request was successful
            status_code: HTTP status code (optional)
            response_data: Response data containing usage information (optional)
        """
        try:
            current_time = time.time()
            key.requests_count += 1
            key.last_request_time = current_time
            
            if success:
                key.success_count += 1
                key.consecutive_errors = 0
                
                # Update token usage if available in response data
                if response_data and 'usage' in response_data:
                    usage = response_data['usage']
                    
                    # Update token counts
                    if 'total_tokens' in usage:
                        key.total_tokens += usage['total_tokens']
                    if 'prompt_tokens' in usage:
                        key.input_tokens += usage['prompt_tokens']
                    if 'completion_tokens' in usage:
                        key.output_tokens += usage['completion_tokens']
                    
                    # Calculate and update cost (provider-specific)
                    cost = self._calculate_usage_cost(key.provider, usage, response_data.get('model'))
                    if cost > 0:
                        key.cost += cost
                
                # Update latency if start_time is in context
                if 'request_start_time' in response_data:
                    latency = current_time - response_data['request_start_time']
                    # Update average latency with exponential moving average
                    if key.avg_latency == 0:
                        key.avg_latency = latency
                    else:
                        key.avg_latency = 0.9 * key.avg_latency + 0.1 * latency
            else:
                key.error_count += 1
                key.consecutive_errors += 1
                
                # Store error information
                if 'error' in response_data:
                    key.last_error = str(response_data['error'])[:255]  # Limit length
                
                # Handle rate limiting
                if status_code == 429:
                    # Set rate limit with exponential backoff based on consecutive failures
                    backoff_seconds = min(60 * (2 ** (key.consecutive_errors - 1)), 3600)  # Max 1 hour
                    key.rate_limited_until = current_time + backoff_seconds
                    logger.warning(f"API key rate limited: {key.id}, backoff: {backoff_seconds}s")
                elif status_code in [401, 403]:
                    # Disable key for authentication errors
                    key.enabled = False
                    logger.error(f"API key disabled due to auth error: {key.id}")
                elif status_code >= 500:
                    # Temporary backoff for server errors
                    key.rate_limited_until = current_time + 30  # 30 second backoff
                    logger.warning(f"API key temporary backoff due to server error: {key.id}")
            
            # Check if key needs rotation
            if key.needs_rotation:
                self._flag_key_for_rotation(key)
                    
        except Exception as e:
            logger.error(f"Error updating key stats: {e}")
    
    def _calculate_usage_cost(self, provider: str, usage: Dict[str, int], model: Optional[str] = None) -> float:
        """
        Calculate the cost of a request based on token usage.
        
        Args:
            provider: The LLM provider
            usage: Token usage information
            model: Model name
            
        Returns:
            Estimated cost in USD
        """
        try:
            # Default pricing (very simplified - in production would use a more complete pricing table)
            pricing = {
                'openai': {
                    'gpt-4': {'input': 0.00003, 'output': 0.00006},
                    'gpt-3.5-turbo': {'input': 0.000001, 'output': 0.000002},
                    'default': {'input': 0.000005, 'output': 0.00001}
                },
                'anthropic': {
                    'claude-3-opus': {'input': 0.00003, 'output': 0.00015},
                    'claude-3-sonnet': {'input': 0.000013, 'output': 0.000038},
                    'claude-3-haiku': {'input': 0.000002, 'output': 0.000015},
                    'default': {'input': 0.00001, 'output': 0.00003}
                },
                'gemini': {
                    'gemini-pro': {'input': 0.000001, 'output': 0.000002},
                    'default': {'input': 0.000001, 'output': 0.000002}
                },
                'deepseek': {
                    'default': {'input': 0.000002, 'output': 0.000004}
                },
                'default': {'input': 0.000005, 'output': 0.00001}
            }
            
            # Get pricing for provider and model
            provider_pricing = pricing.get(provider, pricing['default'])
            model_pricing = provider_pricing.get(model, provider_pricing.get('default', pricing['default']))
            
            # Calculate cost
            input_tokens = usage.get('prompt_tokens', 0)
            output_tokens = usage.get('completion_tokens', 0)
            
            input_cost = input_tokens * model_pricing['input']
            output_cost = output_tokens * model_pricing['output']
            
            return input_cost + output_cost
        except Exception as e:
            logger.error(f"Error calculating usage cost: {e}")
            return 0.0
    
    def _flag_key_for_rotation(self, key: ApiKey) -> None:
        """
        Flag a key for rotation based on usage patterns.
        
        Args:
            key: The API key to flag for rotation
        """
        try:
            if not hasattr(key, 'flagged_for_rotation') or not key.flagged_for_rotation:
                key.flagged_for_rotation = True
                logger.warning(
                    f"API key {key.id} for provider {key.provider} flagged for rotation. "
                    f"Reason: success_rate={key.success_rate:.2f}, "
                    f"consecutive_errors={key.consecutive_errors}, "
                    f"requests={key.requests_count}"
                )
        except Exception as e:
            logger.error(f"Error flagging key for rotation: {e}")
            
    def rotate_key(self, key: ApiKey, new_key: ApiKey) -> None:
        """
        Rotate an API key with a new one.
        
        Args:
            key: The old API key
            new_key: The new API key to replace it
        """
        try:
            # Store rotation information
            new_key.last_rotation = time.time()
            new_key.requests_at_last_rotation = 0
            
            # Copy over relevant statistics for continuity
            new_key.avg_latency = key.avg_latency
            
            # Mark old key as inactive
            key.enabled = False
            key.flagged_for_rotation = False
            
            logger.info(f"API key rotated: old_key={key.id}, new_key={new_key.id}")
        except Exception as e:
            logger.error(f"Error rotating API key: {e}")
            
    def get_keys_needing_rotation(self) -> List[ApiKey]:
        """
        Get a list of keys that need rotation.
        
        Returns:
            List of API keys flagged for rotation
        """
        try:
            return [key for key in self._keys if getattr(key, 'flagged_for_rotation', False)]
        except Exception as e:
            logger.error(f"Error getting keys needing rotation: {e}")
            return []
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategy names."""
        return list(self._strategies.keys())
    
    def get_strategy_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all strategies."""
        stats = {}
        for name, strategy in self._strategies.items():
            stats[name] = {
                "name": strategy.get_strategy_name(),
                "type": type(strategy).__name__
            }
        return stats