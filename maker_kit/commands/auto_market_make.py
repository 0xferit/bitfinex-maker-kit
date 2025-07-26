"""
Auto-market-make command - Automated market making with dynamic center adjustment.
"""

import asyncio
import signal
import sys
from typing import Optional
from ..bitfinex_client import Order, Notification
from ..utilities.market_data import validate_center_price, resolve_center_price
from ..utilities.constants import DEFAULT_SYMBOL, DEFAULT_LEVELS, DEFAULT_SPREAD_PCT, DEFAULT_ORDER_SIZE
from ..services.container import ServiceContainer
from ..config.trading_config import TradingConfig


class AutoMarketMaker:
    """
    Orchestrates automated market making using focused components.
    
    This class now serves as a thin orchestration layer that coordinates
    the various focused components for order management, UI, WebSocket handling,
    and order generation.
    """
    
    def __init__(self, symbol: str, center_price: float, levels: int, spread_pct: float, 
                 size: float, side_filter: Optional[str] = None, test_only: bool = False,
                 ignore_validation: bool = False, yes: bool = False, 
                 container: Optional[ServiceContainer] = None):
        """Initialize orchestrator with dependency injection."""
        self.symbol = symbol
        self.initial_center = center_price
        self.current_center = center_price
        self.levels = levels
        self.spread_pct = spread_pct
        self.size = size
        self.side_filter = side_filter
        self.test_only = test_only
        self.ignore_validation = ignore_validation
        self.yes = yes
        self.running = False
        self.replenish_task = None
        
        # Use provided container or create new one
        self.container = container if container else ServiceContainer()
        
        # Get trading service through DI
        self.trading_service = self.container.create_trading_service()
        self.client = self.trading_service.get_client()
        
        # Initialize focused components using DI
        self.order_manager = self.container.create_order_manager(symbol, levels, spread_pct, size, side_filter)
        self.ui = self.container.create_market_maker_ui(symbol, center_price, levels, spread_pct, size, side_filter)
        self.websocket_handler = self.container.create_websocket_handler(self.order_manager)
        self.order_generator = self.container.create_order_generator(levels, spread_pct, size, side_filter)
        
        # Set up component callbacks
        self._setup_component_callbacks()
    
    def _setup_component_callbacks(self):
        """Set up callbacks between components."""
        # Set UI callback for order manager and WebSocket handler
        self.websocket_handler.set_ui_callback(self.ui.log_message)
        
        # Set order fill callback for center price adjustment
        self.websocket_handler.set_order_fill_callback(self._handle_order_fill)
        
        # Set order cancellation callback
        self.websocket_handler.set_order_cancelled_callback(self._handle_order_cancelled)
    
    async def _handle_order_fill(self, fill_price: float, fill_type: str):
        """Handle order fills by adjusting center price."""
        await self.adjust_orders(fill_price)
    
    def _handle_order_cancelled(self, order_id, order_info):
        """Handle order cancellation events."""
        # Order is already removed from tracking by the WebSocket handler
        pass
        
    def validate_initial_price(self):
        """Validate initial center price using existing validation."""
        is_valid, range_info = validate_center_price(self.symbol, self.initial_center, self.ignore_validation)
        if not is_valid:
            if range_info:
                error_msg = (f"Invalid center price: ${self.initial_center:.6f} is outside the current bid-ask spread. "
                           f"Valid range: ${range_info['bid']:.6f} < center price < ${range_info['ask']:.6f}")
            else:
                error_msg = f"Invalid center price: ${self.initial_center:.6f} (unable to get current market data)"
            raise ValueError(error_msg)
    
    def place_initial_orders(self):
        """Place initial set of orders using order manager."""
        return self.order_manager.place_initial_orders(self.current_center, self.ui.log_message)
    
    def cancel_all_orders(self):
        """Cancel all active orders using order manager."""
        self.order_manager.cancel_all_orders(self.ui.log_message)
    
    def check_and_replenish_orders(self):
        """Check for cancelled orders and replenish them using order manager."""
        return self.order_manager.check_and_replenish_orders(self.ui.log_message)
    
    async def periodic_replenishment(self):
        """Periodic task to replenish cancelled orders every 30 seconds"""
        # Initial delay to let orders settle
        await asyncio.sleep(30)
        
        while self.running:
            try:
                if self.running:  # Check again in case we're shutting down
                    self.check_and_replenish_orders()
                await asyncio.sleep(30)  # Wait 30 seconds for next check
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n❌ Error in periodic replenishment: {e}")
    
    async def adjust_orders(self, new_center: float):
        """Cancel existing orders and place new ones around new center using components."""
        # Generate new orders for preview
        new_orders = self.order_generator.generate_orders(new_center)
        
        # Use UI to display adjustment preview
        self.ui.display_order_adjustment_preview(new_center, new_orders)
        
        # Cancel existing orders
        self.cancel_all_orders()
        await asyncio.sleep(1)  # Brief pause to ensure cancellations process
        
        # Update current center
        self.current_center = new_center
        
        # Place new orders
        self.place_initial_orders()
    
    def setup_websocket_handlers(self):
        """Setup WebSocket event handlers using the WebSocket handler component."""
        self.websocket_handler.setup_handlers()
    
    async def start(self):
        """Start the auto market maker using coordinated components."""
        # Phase 1: Setup and validation
        if not await self._prepare_startup():
            return
        
        # Phase 2: Initial order placement
        if not self._place_and_verify_initial_orders():
            return
            
        # Phase 3: Test mode completion or continuous monitoring
        if self.test_only:
            self.ui.display_test_complete()
            return
        
        # Phase 4: Start continuous monitoring
        await self._start_continuous_monitoring()
    
    async def _prepare_startup(self) -> bool:
        """
        Prepare for startup by validating configuration and confirming with user.
        
        Returns:
            True if startup should continue, False if cancelled
        """
        # Display startup info
        self.ui.display_startup_info(self.test_only)
        
        # Validate initial price
        self.validate_initial_price()
        
        # Generate initial orders for preview
        initial_orders = self.order_generator.generate_orders(self.initial_center)
        
        # Confirm startup with user
        if not self.ui.confirm_startup(initial_orders, self.test_only, self.yes):
            self.ui.log_message("❌ Auto market maker cancelled")
            return False
        
        return True
    
    def _place_and_verify_initial_orders(self) -> bool:
        """
        Place initial orders and verify they were successful.
        
        Returns:
            True if orders were placed successfully, False otherwise
        """
        # Place initial orders
        self.place_initial_orders()
        
        # Check if orders were placed successfully
        tracked_orders = self.order_manager.get_tracked_orders()
        if not tracked_orders:
            self.ui.log_message("❌ No orders were placed successfully. Exiting.")
            return False
        
        # Calculate initial order count for display
        initial_orders = self.order_generator.generate_orders(self.initial_center)
        self.ui.display_placement_complete(len(tracked_orders), len(initial_orders))
        
        return True
    
    async def _start_continuous_monitoring(self):
        """Start continuous WebSocket monitoring and periodic tasks."""
        # Setup WebSocket monitoring
        self.ui.display_websocket_status()
        self.setup_websocket_handlers()
        
        # Start monitoring loop
        self.running = True
        try:
            await self.client.wss.start()
            
            # Start periodic replenishment task
            self.replenish_task = asyncio.create_task(self.periodic_replenishment())
            self.ui.display_replenishment_start()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.ui.display_shutdown_start()
            await self.stop()
    
    async def stop(self):
        """Stop the auto market maker and clean up using components."""
        self.running = False
        
        # Cancel periodic replenishment task
        if self.replenish_task:
            self.replenish_task.cancel()
            try:
                await self.replenish_task
            except asyncio.CancelledError:
                pass
            self.ui.log_message("🔄 Stopped periodic replenishment")
        
        # Cancel all remaining orders
        self.ui.log_message("🗑️  Cancelling all remaining orders...")
        self.cancel_all_orders()
        
        # Close WebSocket connection
        await self.client.wss.close()
        self.ui.display_shutdown_complete()


async def auto_market_make(symbol: str, center_price: float, levels: int, spread_pct: float, 
                          size: float, side_filter: Optional[str] = None, test_only: bool = False,
                          ignore_validation: bool = False, yes: bool = False,
                          container: Optional[ServiceContainer] = None):
    """Start auto market maker with dynamic center adjustment using dependency injection"""
    
    try:
        # Create or use provided container
        if container is None:
            container = ServiceContainer()
            # Configure with appropriate settings
            config = TradingConfig()
            container.configure(config.to_dict())
        
        amm = AutoMarketMaker(symbol, center_price, levels, spread_pct, size, side_filter, 
                             test_only, ignore_validation, yes, container)
    except ValueError as e:
        print(f"❌ Failed to start auto market maker: {e}")
        return
    
    # Set up signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Received shutdown signal...")
        # Store task reference to prevent garbage collection
        _ = asyncio.create_task(amm.stop())  # noqa: RUF006
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await amm.start() 


def auto_market_make_command(symbol: str = DEFAULT_SYMBOL, center: str = None, 
                           levels: int = DEFAULT_LEVELS, spread: float = DEFAULT_SPREAD_PCT, 
                           size: float = DEFAULT_ORDER_SIZE, buy_only: bool = False, 
                           sell_only: bool = False, test_only: bool = False,
                           ignore_validation: bool = False, yes: bool = False):
    """Automated market making with dynamic center adjustment"""
    
    # Determine side filter
    side_filter = None
    if buy_only:
        side_filter = "buy"
    elif sell_only:
        side_filter = "sell"
    
    # Resolve center price from string input
    center_price = resolve_center_price(symbol, center)
    if center_price is None:
        return  # Error already printed by resolve_center_price
    
    return asyncio.run(auto_market_make(symbol, center_price, levels, spread, size, side_filter, test_only, ignore_validation, yes))