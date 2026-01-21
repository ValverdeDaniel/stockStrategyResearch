"""
Data caching module for efficient data management
"""

import pandas as pd
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any
import hashlib
import json


class DataCache:
    """Manages caching of fetched data and calculated indicators"""

    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize data cache

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}
        self.cache_expiry_hours = 1  # Cache expiry time

    def _generate_key(self, **kwargs) -> str:
        """
        Generate a unique cache key from parameters

        Args:
            **kwargs: Parameters to include in the key

        Returns:
            Unique hash key
        """
        key_str = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str, **kwargs) -> Optional[Any]:
        """
        Retrieve data from cache

        Args:
            key: Base key for the cache entry
            **kwargs: Additional parameters for key generation

        Returns:
            Cached data if available and not expired, None otherwise
        """
        cache_key = f"{key}_{self._generate_key(**kwargs)}"

        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if self._is_valid_cache(entry['timestamp']):
                return entry['data']

        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                    if self._is_valid_cache(entry['timestamp']):
                        # Load into memory cache
                        self.memory_cache[cache_key] = entry
                        return entry['data']
            except Exception as e:
                print(f"Error loading cache: {e}")

        return None

    def set(self, key: str, data: Any, **kwargs) -> None:
        """
        Store data in cache

        Args:
            key: Base key for the cache entry
            data: Data to cache
            **kwargs: Additional parameters for key generation
        """
        cache_key = f"{key}_{self._generate_key(**kwargs)}"

        entry = {
            'data': data,
            'timestamp': datetime.now(),
            'params': kwargs
        }

        # Store in memory cache
        self.memory_cache[cache_key] = entry

        # Store on disk
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _is_valid_cache(self, timestamp: datetime) -> bool:
        """
        Check if cache entry is still valid

        Args:
            timestamp: Timestamp of cache entry

        Returns:
            True if cache is valid, False if expired
        """
        age = datetime.now() - timestamp
        return age < timedelta(hours=self.cache_expiry_hours)

    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear cache entries

        Args:
            key: Specific key to clear, or None to clear all
        """
        if key:
            # Clear specific key
            pattern = f"{key}_*"
            for cache_file in self.cache_dir.glob(f"{pattern}.pkl"):
                cache_file.unlink()

            # Clear from memory
            keys_to_remove = [k for k in self.memory_cache if k.startswith(f"{key}_")]
            for k in keys_to_remove:
                del self.memory_cache[k]
        else:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            self.memory_cache.clear()

        print(f"Cache cleared: {key or 'all'}")

    def get_cached_dataframe(
        self,
        key: str,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve a DataFrame from cache

        Args:
            key: Cache key
            **kwargs: Additional parameters

        Returns:
            Cached DataFrame or None
        """
        data = self.get(key, **kwargs)
        if data is not None and isinstance(data, pd.DataFrame):
            return data.copy()
        return None

    def set_dataframe(
        self,
        key: str,
        df: pd.DataFrame,
        **kwargs
    ) -> None:
        """
        Cache a DataFrame

        Args:
            key: Cache key
            df: DataFrame to cache
            **kwargs: Additional parameters
        """
        self.set(key, df.copy(), **kwargs)

    def get_cache_info(self) -> dict:
        """
        Get information about current cache status

        Returns:
            Dictionary with cache statistics
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)  # MB

        return {
            'memory_entries': len(self.memory_cache),
            'disk_entries': len(cache_files),
            'total_size_mb': round(total_size, 2),
            'cache_dir': str(self.cache_dir),
            'expiry_hours': self.cache_expiry_hours
        }