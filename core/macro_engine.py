import pandas as pd
import requests
import io
import datetime

def get_fred_data(series_id):
    """Fetches a specific FRED series as a DataFrame using the public CSV link."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return pd.DataFrame()
        
        df = pd.read_csv(io.StringIO(response.text))
        df['observation_date'] = pd.to_datetime(df['observation_date'])
        
        # Clean data (handle '.' which FRED uses for missing values)
        df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
        df = df.dropna().set_index('observation_date')
        return df
    except Exception as e:
        print(f"Error fetching {series_id}: {e}")
        return pd.DataFrame()

def get_macro_context():
    """Compiles a unified Macro DataFrame with key economic indicators."""
    # 1. 10Y-2Y Yield Spread (Recession Indicator)
    yield_curve = get_fred_data("T10Y2Y")
    
    # 2. Fed Funds Effective Rate (Monetary Policy)
    fed_funds = get_fred_data("FEDFUNDS")
    
    if yield_curve.empty and fed_funds.empty:
        return pd.DataFrame()
        
    # Join indicators
    macro_df = yield_curve.join(fed_funds, how='outer').ffill()
    
    # Add simple momentum indicators
    if not macro_df.empty:
        macro_df['Yield_Momentum'] = macro_df['T10Y2Y'].diff(20) # 1-month-ish momentum
        macro_df['Fed_Policy_Bias'] = macro_df['FEDFUNDS'].diff(60) # 3-month-ish trend
        
    return macro_df

if __name__ == "__main__":
    # Unit Test
    print("Fetching Macro Data...")
    ctx = get_macro_context()
    if not ctx.empty:
        print("Latest Macro Context:")
        print(ctx.tail())
    else:
        print("Failed to fetch macro data.")
