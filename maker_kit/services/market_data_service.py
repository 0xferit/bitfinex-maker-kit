"""
Enhanced market data service with caching and performance optimizations.

Provides high-performance market data operations with intelligent caching,
batch fetching, and real-time data management.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from ..utilities.market_data_cache import MarketDataCache, MarketDataType, MarketDataCacheConfig, create_market_data_cache
from ..domain.symbol import Symbol
from ..services.container import ServiceContainer

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Enhanced market data service with caching and performance optimizations.
    
    Provides high-level market data operations with intelligent caching,
    reducing API calls and improving response times.
    """
    
    def __init__(self, container: ServiceContainer, 
                 cache_config: Optional[MarketDataCacheConfig] = None):
        """
        Initialize market data service.
        
        Args:
            container: Service container for dependency injection
            cache_config: Optional cache configuration
        """
        self.container = container
        self.cache = create_market_data_cache(cache_config)
        self._client = None
        
        # Setup data providers
        self._setup_data_providers()
        
        # Performance tracking
        self._api_calls = 0
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _setup_data_providers(self) -> None:
        """Setup data providers for cache warming."""
        # Register ticker data provider
        async def fetch_ticker(symbol: str) -> Dict[str, Any]:
            client = self._get_client()
            try:
                ticker = client.get_ticker(symbol)
                self._api_calls += 1
                
                return {
                    'symbol': symbol,
                    'bid': float(ticker.bid),
                    'ask': float(ticker.ask),
                    'last_price': float(ticker.last_price),
                    'bid_size': float(ticker.bid_size),
                    'ask_size': float(ticker.ask_size),
                    'timestamp': ticker.timestamp if hasattr(ticker, 'timestamp') else None
                }
            except Exception as e:
                logger.error(f"Error fetching ticker for {symbol}: {e}")
                raise
        
        # Register order book data provider
        async def fetch_orderbook(symbol: str, precision: str = "P0") -> Dict[str, Any]:
            client = self._get_client()
            try:
                orderbook = client.get_orderbook(symbol, precision=precision)
                self._api_calls += 1
                
                return {
                    'symbol': symbol,
                    'precision': precision,
                    'bids': [[float(bid.price), float(bid.amount)] for bid in orderbook.bids[:10]],
                    'asks': [[float(ask.price), float(ask.amount)] for ask in orderbook.asks[:10]],
                    'timestamp': orderbook.timestamp if hasattr(orderbook, 'timestamp') else None
                }
            except Exception as e:
                logger.error(f"Error fetching orderbook for {symbol}: {e}")
                raise
        
        # Register account balance provider
        async def fetch_balance() -> List[Dict[str, Any]]:
            client = self._get_client()
            try:
                wallets = client.get_wallets()
                self._api_calls += 1
                
                return [
                    {
                        'currency': wallet.currency,
                        'type': wallet.type,
                        'balance': float(wallet.balance),
                        'available': float(wallet.available) if hasattr(wallet, 'available') else None
                    }
                    for wallet in wallets
                ]
            except Exception as e:
                logger.error(f"Error fetching account balance: {e}")
                raise
        
        # Register trades data provider
        async def fetch_trades(symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
            client = self._get_client()
            try:
                trades = client.get_trades(symbol, limit=limit)
                self._api_calls += 1
                
                return [
                    {
                        'price': float(trade.price),
                        'amount': float(trade.amount),
                        'timestamp': trade.timestamp if hasattr(trade, 'timestamp') else None,
                        'side': 'buy' if float(trade.amount) > 0 else 'sell'
                    }
                    for trade in trades
                ]
            except Exception as e:
                logger.error(f"Error fetching trades for {symbol}: {e}")
                raise
        
        # Register all providers with cache
        self.cache.register_data_provider(MarketDataType.TICKER, fetch_ticker)
        self.cache.register_data_provider(MarketDataType.ORDER_BOOK, fetch_orderbook)
        self.cache.register_data_provider(MarketDataType.ACCOUNT_BALANCE, fetch_balance)
        self.cache.register_data_provider(MarketDataType.TRADES, fetch_trades)
    
    def _get_client(self):
        """Get trading client from container."""
        if self._client is None:
            trading_service = self.container.create_trading_service()
            self._client = trading_service.get_client()
        return self._client
    
    async def get_ticker(self, symbol: Symbol, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get ticker data with caching.
        
        Args:
            symbol: Trading symbol
            use_cache: Whether to use cache
            
        Returns:
            Ticker data or None if not available
        """
        try:
            result = await self.cache.get_ticker(symbol, force_refresh=not use_cache)
            
            if result is not None:
                if use_cache:
                    self._cache_hits += 1
                else:
                    self._cache_misses += 1
            else:
                self._cache_misses += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_orderbook(self, symbol: Symbol, precision: str = "P0",
                          use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get order book data with caching.
        
        Args:
            symbol: Trading symbol
            precision: Order book precision
            use_cache: Whether to use cache
            
        Returns:
            Order book data or None if not available
        """
        try:
            result = await self.cache.get_order_book(symbol, precision, force_refresh=not use_cache)
            
            if result is not None:
                if use_cache:
                    self._cache_hits += 1
                else:
                    self._cache_misses += 1
            else:
                self._cache_misses += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return None
    
    async def get_account_balance(self, use_cache: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        Get account balance with caching.
        
        Args:
            use_cache: Whether to use cache
            
        Returns:
            Account balance data or None if not available
        """
        try:
            result = await self.cache.get_account_balance(force_refresh=not use_cache)
            
            if result is not None:
                if use_cache:
                    self._cache_hits += 1
                else:
                    self._cache_misses += 1
            else:
                self._cache_misses += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return None
    
    async def get_recent_trades(self, symbol: Symbol, limit: int = 50,
                              use_cache: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        Get recent trades with caching.
        
        Args:
            symbol: Trading symbol
            limit: Number of trades to fetch
            use_cache: Whether to use cache
            
        Returns:
            Recent trades data or None if not available
        """
        try:
            result = await self.cache.get_recent_trades(symbol, limit, force_refresh=not use_cache)
            
            if result is not None:
                if use_cache:
                    self._cache_hits += 1
                else:
                    self._cache_misses += 1
            else:
                self._cache_misses += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting recent trades for {symbol}: {e}")
            return None
    
    async def get_multiple_tickers(self, symbols: List[Symbol],
                                 use_cache: bool = True) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get multiple tickers efficiently.
        
        Args:
            symbols: List of trading symbols
            use_cache: Whether to use cache
            
        Returns:
            Dictionary mapping symbol strings to ticker data
        """
        try:
            results = await self.cache.batch_get_tickers(symbols, force_refresh=not use_cache)
            
            # Update cache statistics
            for result in results.values():
                if result is not None:
                    if use_cache:
                        self._cache_hits += 1
                    else:
                        self._cache_misses += 1
                else:
                    self._cache_misses += 1
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting multiple tickers: {e}")
            return {}
    
    async def suggest_price_centers(self, symbol: Symbol) -> Optional[Dict[str, float]]:
        """
        Suggest appropriate price centers based on market data.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with suggested price centers
        """
        try:
            # Get ticker data
            ticker = await self.get_ticker(symbol)
            if not ticker:
                return None
            
            # Get recent trades
            trades = await self.get_recent_trades(symbol, limit=10)
            
            bid = ticker.get('bid', 0)
            ask = ticker.get('ask', 0)
            last_price = ticker.get('last_price', 0)
            
            if bid <= 0 or ask <= 0:
                return None
            
            mid_price = (bid + ask) / 2
            
            # Calculate price centers
            suggestions = {
                'bid': bid,
                'ask': ask,
                'mid_price': mid_price,
                'last_price': last_price,
                'bid_weighted': bid + (ask - bid) * 0.3,  # 30% towards ask
                'ask_weighted': ask - (ask - bid) * 0.3,  # 30% towards bid
            }
            
            # Add trade-based suggestions if available
            if trades and len(trades) > 0:
                recent_prices = [trade['price'] for trade in trades[:5]]
                avg_recent = sum(recent_prices) / len(recent_prices)
                suggestions['recent_avg'] = avg_recent
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting price centers for {symbol}: {e}")
            return None
    
    async def get_market_summary(self, symbols: List[Symbol]) -> Dict[str, Any]:
        """
        Get market summary for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            Market summary data
        """
        try:
            # Get all tickers efficiently
            tickers = await self.get_multiple_tickers(symbols)
            
            summary = {
                'timestamp': asyncio.get_event_loop().time(),
                'symbols_count': len(symbols),
                'active_symbols': 0,
                'total_volume': 0.0,
                'avg_spread_pct': 0.0,
                'symbols': {}
            }
            
            spreads = []
            
            for symbol_str, ticker in tickers.items():
                if ticker:
                    summary['active_symbols'] += 1
                    
                    bid = ticker.get('bid', 0)
                    ask = ticker.get('ask', 0)
                    
                    if bid > 0 and ask > 0:
                        spread_pct = ((ask - bid) / bid) * 100
                        spreads.append(spread_pct)
                    
                    summary['symbols'][symbol_str] = {
                        'bid': bid,
                        'ask': ask,
                        'last_price': ticker.get('last_price', 0),
                        'spread_pct': spread_pct if bid > 0 and ask > 0 else None
                    }
            
            if spreads:
                summary['avg_spread_pct'] = sum(spreads) / len(spreads)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {}
    
    async def start_cache_warming(self) -> None:
        """Start background cache warming."""
        await self.cache.start_background_warming()
        logger.info("Market data cache warming started")
    
    async def stop_cache_warming(self) -> None:
        """Stop background cache warming."""
        await self.cache.stop_background_warming()
        logger.info("Market data cache warming stopped")
    
    async def invalidate_symbol_cache(self, symbol: Symbol) -> int:
        """
        Invalidate cached data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Number of cache entries invalidated
        """
        return await self.cache.invalidate_symbol_data(symbol)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        cache_stats = self.cache.get_cache_stats()
        
        total_requests = self._cache_hits + self._cache_misses
        cache_hit_ratio = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        api_reduction_pct = 0.0
        if total_requests > 0:
            api_reduction_pct = (1 - (self._api_calls / total_requests)) * 100
        
        return {
            'cache_hit_ratio': cache_hit_ratio,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'api_calls': self._api_calls,
            'total_requests': total_requests,
            'api_reduction_pct': api_reduction_pct,
            'cache_stats': cache_stats
        }
    
    async def cleanup(self) -> None:
        """Clean up market data service resources."""
        await self.cache.cleanup()
        logger.info("Market data service cleaned up")


def create_market_data_service(container: ServiceContainer,
                             cache_config: Optional[MarketDataCacheConfig] = None) -> MarketDataService:
    """
    Create market data service with caching.
    
    Args:
        container: Service container
        cache_config: Optional cache configuration
        
    Returns:
        Configured MarketDataService instance
    """
    return MarketDataService(container, cache_config)