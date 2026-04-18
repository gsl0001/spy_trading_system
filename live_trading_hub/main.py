import asyncio

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from ib_insync import *

from live_trading_hub.data_streamer import DataStreamer
from live_trading_hub.strategy_engine import StrategyEngine
from live_trading_hub.execution_engine import ExecutionEngine

class IBKRBot:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        
        self.streamer = DataStreamer(self.ib)
        self.strategy = StrategyEngine(ai_confidence_threshold=0.60)
        self.executor = ExecutionEngine(self.ib)
        
        # Load pre-trained model (if available)
        import os
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core', 'models', 'my_0dte_model.pkl')
        self.strategy.load_ai_model(model_path)
        
        # State tracking
        self.in_position = False

    async def connect(self):
        try:
            await self.ib.connectAsync(self.host, self.port, self.client_id)
            print("Connected to IBKR.")
        except Exception as e:
            print(f"\n[ERROR] Failed to connect to IBKR on {self.host}:{self.port}: {e}")
            print("--> Please ensure that Interactive Brokers TWS or IB Gateway is running.")
            print("--> Verify that API connections are enabled in Settings -> API -> Settings.")
            print("--> Ensure the 'Socket port' matches 7497 (Paper) or 7496 (Live).\n")
            raise

    def on_new_bar(self, df):
        if self.in_position:
            # Note: For scaffolding, we are just placing a trade once.
            # Real logic would monitor trailing stops / take profits here.
            return
            
        print(f"Evaluating Bar: {df.index[-1]} | Close: {df['Close'].iloc[-1]}")
        decision = self.strategy.evaluate_bar(df)
        
        if decision['signal'] != "NONE":
            print(f"*** SIGNAL GENERATED: {decision['signal']} | AI Confidence: {decision['confidence']:.2f} ***")
            
            # Fire and forget execution asynchronously
            # We use a task so it doesn't block the data streamer
            asyncio.create_task(self.execute_trade(decision['signal'], df['Close'].iloc[-1]))

    async def execute_trade(self, direction, current_price):
        self.in_position = True # Prevent multiple trades firing
        success = await self.executor.execute_combo(direction, current_price)
        if not success:
            print("Trade failed. Resetting position state.")
            self.in_position = False

    async def run(self):
        await self.connect()
        
        # Attach strategy evaluation to the data streamer
        self.streamer.on_new_bar_callbacks.append(self.on_new_bar)
        
        # Start streaming data
        await self.streamer.request_data()
        
        print("Bot is live. Waiting for market action...")
        
        # Keep loop running unconditionally
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    bot = IBKRBot(port=7497) # Use 7497 for paper trading
    try:
        loop = asyncio.get_event_loop()
        task = loop.create_task(bot.run())
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        print("\nShutting down bot...")
        bot.ib.disconnect()
    except Exception as e:
        print(f"\nSystem Exited: {e}")
        bot.ib.disconnect()
