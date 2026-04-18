import numpy as np
from scipy.stats import norm
import scipy.optimize as optimize

class BlackScholesPricer:
    """
    Theoretical Options Pricing built on the Black-Scholes-Merton model.
    Used for historical backtesting when true options chains are unavailable.
    """
    
    @staticmethod
    def _d1(S, K, T, r, sigma):
        # Add small epsilon to T to prevent division by zero near expiration
        T = max(T, 1e-4)
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def _d2(S, K, T, r, sigma):
        T = max(T, 1e-4)
        return BlackScholesPricer._d1(S, K, T, r, sigma) - sigma * np.sqrt(T)
        
    @staticmethod
    def price(S, K, T, r, sigma, option_type='call'):
        """
        Calculate option theoretical premium.
        S: Spot price
        K: Strike price
        T: Time to expiration (in years, e.g., DTE / 365)
        r: Risk-free interest rate (decimal view)
        sigma: Implied volatility (decimal view)
        """
        if T <= 0: return max(S - K, 0) if option_type == 'call' else max(K - S, 0)
        
        d1 = BlackScholesPricer._d1(S, K, T, r, sigma)
        d2 = BlackScholesPricer._d2(S, K, T, r, sigma)
        
        if option_type == 'call':
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type == 'put':
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            raise ValueError("option_type must be 'call' or 'put'")

    @staticmethod
    def delta(S, K, T, r, sigma, option_type='call'):
        if T <= 0: return 1.0 if (option_type == 'call' and S > K) else (-1.0 if option_type == 'put' and S < K else 0.0)
        d1 = BlackScholesPricer._d1(S, K, T, r, sigma)
        if option_type == 'call':
            return norm.cdf(d1)
        elif option_type == 'put':
            return norm.cdf(d1) - 1

    @staticmethod
    def gamma(S, K, T, r, sigma):
        if T <= 0: return 0.0
        d1 = BlackScholesPricer._d1(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))

    @staticmethod
    def theta(S, K, T, r, sigma, option_type='call'):
        if T <= 0: return 0.0
        d1 = BlackScholesPricer._d1(S, K, T, r, sigma)
        d2 = BlackScholesPricer._d2(S, K, T, r, sigma)
        
        term1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        if option_type == 'call':
            term2 = r * K * np.exp(-r * T) * norm.cdf(d2)
            theta_annual = term1 - term2
        elif option_type == 'put':
            term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
            theta_annual = term1 + term2
            
        return theta_annual / 365.0  # Daily theta

    @staticmethod
    def vega(S, K, T, r, sigma):
        if T <= 0: return 0.0
        d1 = BlackScholesPricer._d1(S, K, T, r, sigma)
        return S * norm.pdf(d1) * np.sqrt(T) / 100.0  # value per 1% change

    @staticmethod
    def get_greeks(S, K, T, r, sigma, option_type='call'):
        return {
            'price': BlackScholesPricer.price(S, K, T, r, sigma, option_type),
            'delta': BlackScholesPricer.delta(S, K, T, r, sigma, option_type),
            'gamma': BlackScholesPricer.gamma(S, K, T, r, sigma),
            'theta': BlackScholesPricer.theta(S, K, T, r, sigma, option_type),
            'vega': BlackScholesPricer.vega(S, K, T, r, sigma)
        }

    @staticmethod
    def find_strike_for_delta(S, T, r, sigma, target_delta, option_type='call'):
        """
        Finds the strike that closely matches a given target delta.
        For robust quantitative backtesting without chain data.
        """
        if option_type == 'put' and target_delta > 0:
            target_delta = -target_delta # Ensure negative representation
            
        def obj_func(K):
            current_delta = BlackScholesPricer.delta(S, K, T, r, sigma, option_type)
            return (current_delta - target_delta)**2
            
        # Initial guess based on spot price (at the money)
        initial_guess = S
        
        # Optimize to find strike
        result = optimize.minimize(obj_func, initial_guess, bounds=[(S*0.5, S*1.5)])
        
        # Round to nearest whole dollar or simple 0.5 increment for SPY typically
        strike = round(result.x[0])
        return strike
