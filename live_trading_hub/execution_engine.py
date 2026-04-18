from ib_insync import *
import asyncio
from loguru import logger

class ExecutionEngine:
    def __init__(self, ib_client: IB):
        self.ib = ib_client

    async def get_0dte_chain(self):
        """Fetches the SPY option chain for 0 DTE."""
        try:
            spy = Stock('SPY', 'SMART', 'USD')
            await self.ib.qualifyContractsAsync(spy)
            
            chains = await self.ib.reqSecDefOptParamsAsync(spy.symbol, '', spy.secType, spy.conId)
            if not chains:
                logger.error("Failed to fetch option chains: No chains returned.")
                return None, None
                
            # Get chain from SMART exchange
            chain = next((c for c in chains if c.exchange == 'SMART'), chains[0])
            
            # Get expirations and find today's 0 DTE
            expirations = sorted(chain.expirations)
            if not expirations:
                logger.error("No expirations found in option chain.")
                return None, None
                
            zero_dte = expirations[0] # assuming the earliest is today
            return chain.strikes, zero_dte
        except Exception as e:
            logger.error(f"Error in get_0dte_chain: {e}")
            return None, None

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
        Returns the ib_insync.Trade object or None.
        """
        strikes, exp_date = await self.get_0dte_chain()
        if not strikes:
            return None
            
        spread_type = "BULL_PUT" if direction == "LONG" else "BEAR_CALL"
        sell_strike, buy_strike = await self.find_strikes(strikes, current_price, spread_type)
        
        right = 'P' if spread_type == "BULL_PUT" else 'C'
        
        # Define Option Contracts
        sell_opt = Option('SPY', exp_date, sell_strike, right, 'SMART')
        buy_opt = Option('SPY', exp_date, buy_strike, right, 'SMART')
        
        await self.ib.qualifyContractsAsync(sell_opt, buy_opt)
        
        # Build Combo Contract (Spread)
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
             logger.warning("No bid/ask available. Defaulting to market order.")
             order = MarketOrder('SELL', 1)
        else:
            mid_price = round((mkt_data.bid + mkt_data.ask) / 2, 2)
            logger.info(f"Calculated Mid Price: {mid_price}")
            # For selling a BAG, we use LimitOrder with a positive limit price if using SELL action
            order = LimitOrder('SELL', 1, mid_price)
        
        self.ib.cancelMktData(contract)
        
        logger.info(f"Placing {spread_type} 0 DTE ({sell_strike}/{buy_strike}) @ {order.orderType}: {getattr(order, 'lmtPrice', 'MKT')}")
        
        # Margin Verification
        try:
            what_if = self.ib.whatIfOrder(contract, order)
            if what_if and hasattr(what_if, 'initMarginChange'):
                margin_change = float(what_if.initMarginChange)
                logger.info(f"Margin Impact Verification: {margin_change}")
                # Optional: Check against account summary here if needed
        except Exception as e:
            logger.error(f"Margin Verification failed: {e}. Rejecting trade.")
            return None
        
        try:
            trade = self.ib.placeOrder(contract, order)
            # Wait briefly for order to be acknowledged
            await asyncio.sleep(0.5)
            logger.info(f"Trade placed! Order Status: {trade.orderStatus.status}")
            return trade
        except Exception as e:
            logger.error(f"Error placing trade: {e}")
            return None

    async def close_position(self, contract):
        """Closes an open position by placing an offsetting market order."""
        logger.info(f"Closing position for contract: {contract.symbol} {contract.secType}")
        # For a BAG sold originally, we need to BUY it back
        order = MarketOrder('BUY', 1)
        try:
            trade = self.ib.placeOrder(contract, order)
            await asyncio.sleep(0.5)
            logger.info(f"Close order placed! Status: {trade.orderStatus.status}")
            return trade
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None
