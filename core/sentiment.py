import pandas as pd
import requests
import io

def get_insider_sentiment():
    """Fetches and processes insider buy/sell ratio from OpenInsider."""
    url = "http://openinsider.com/ps_data.csv"
    try:
        # Reduced timeout to prevents app hanging
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return pd.DataFrame()

        df = pd.read_csv(io.StringIO(response.text), sep='\t')
        
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
        
        # Filter out invalid rows (e.g. 0 date)
        df = df[df['Date'] > 100].copy()
        
        # Parse YYMMDD
        df['Date_Str'] = df['Date'].astype(str).str.zfill(6)
        df['dt'] = pd.to_datetime(df['Date_Str'], format='%y%m%d', errors='coerce')
        df = df.dropna(subset=['dt']).sort_values('dt').set_index('dt')
        
        # Calculate Buy Momentum
        purchases_10 = df['Purchases'].rolling(window=10).mean()
        purchases_50 = df['Purchases'].rolling(window=50).mean()
        
        df['Insider_Sentiment'] = (purchases_10 / purchases_50.replace(0, 1)).fillna(1.0)
        
        return df[['Insider_Sentiment']]
    except Exception:
        # Silent fallback to prevent UI stalling
        return pd.DataFrame()

if __name__ == "__main__":
    # Test fetch
    res = get_insider_sentiment()
    print(res.tail())
