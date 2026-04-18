from ib_insync import *
import asyncio

class ExecutionEngine:
    def __init__(self, ib_client: IB):
        self.ib = ib_client

    async def get_0dte_chain(self):
        """Fetches the SPY option chain for 0 DTE."""
        spy = Stock('SPY', 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(spy)
        
        chains = await self.ib.reqSecDefOptParamsAsync(spy.symbol, '', spy.secType, spy.conId)
        if not chains:
            print("Failed to fetch option chains.")
            return None
            
        # Get chain from SMART exchange
        chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
        
        # Get expirations and find today's 0 DTE
        expirations = sorted(chain.expirations)
        if not expirations:
            return None
            
        zero_dte = expirations[0] # assuming the earliest is today
        return chain.strikes, zero_dte

    async def find_strikes(self, strikes, current_price, spread_type, width=1.0):
        """Selects strikes based on proximity to current price (ATM credit spread)."""
        closest_strike = min(strikes, key=lambda x: abs(x - current_price))
        
        if spread_type == "BULL_PUT":
            sell_strike = closest_strike
            buy_strike = sell_strike - width
        else: # BEAR_CALL
            sell_strike = closest_strike
            buy_strike = sell_strike + width
            
        return sell_strike, buy_strike

    async def execute_combo(self, direction, current_price):
        """
        Main execution routing for placing a Credit Spread order.
        direction: "LONG" (Bull Put Spread) or "SHORT" (Bear Call Spread)
        """
        strikes, exp_date = await self.get_0dte_chain()
        if not strikes:
            return False
            
        spread_type = "BULL_PUT" if direction == "LONG" else "BEAR_CALL"
        sell_strike, buy_strike = await self.find_strikes(strikes, current_price, spread_type)
        
        right = 'P' if spread_type == "BULL_PUT" else 'C'
        
        # Define Option Contracts
        sell_opt = Option('SPY', exp_date, sell_strike, right, 'SMART')
        buy_opt = Option('SPY', exp_date, buy_strike, right, 'SMART')
        
        await self.ib.qualifyContractsAsync(sell_opt, buy_opt)
        
        # Build Combo Contract (Spread)
        # Ratio 1:1, action -1 (sell), action 1 (buy)
        contract = Contract()
        contract.symbol = 'SPY'
        contract.secType = 'BAG'
        contract.currency = 'USD'
        contract.exchange = 'SMART'
        
        leg1 = ComboLeg()
        leg1.conId = sell_opt.conId
        leg1.ratio = 1
        leg1.action = 'SELL'
        leg1.exchange = 'SMART'
        
        leg2 = ComboLeg()
        leg2.conId = buy_opt.conId
        leg2.ratio = 1
        leg2.action = 'BUY'
        leg2.exchange = 'SMART'
        
        contract.comboLegs = [leg1, leg2]
        
        # Request market data for the combo to price it mid
        mkt_data = self.ib.reqMktData(contract, "", False, False)
        # Wait for data to populate
        await asyncio.sleep(2)
        
        mid_price = None
        if mkt_data.bid != mkt_data.bid and mkt_data.ask != mkt_data.ask:
             print("No bid/ask available. Defaulting to market order or skipping.")
             # Fallback: Can't price securely without bid/ask
             return False
        
        mid_price = round((mkt_data.bid + mkt_data.ask) / 2, 2)
        self.ib.cancelMktData(contract)
        
        print(f"Executing {spread_type} 0 DTE ({sell_strike}/{buy_strike}) @ Mid: {mid_price}")
        
        # Create Order
        # Note: Credit spread LIMIT orders are usually sent as negative price for debit/credit combinations if selling BAG
        # Or using action 'SELL' with a positive limit. IBKR limits for BAGs are tricky.
        # We will use Market Order for this scaffolding to ensure fill, but ideally Limit Order in prod.
        order = MarketOrder('SELL', 1) 
        
        # trade = self.ib.placeOrder(contract, order)
        print("Trade placed (Simulated)!")
        
        return True
