import pandas as pd
import requests
import io

def test_fred():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y"
    try:
        response = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        print("FRED Success!")
        print(df.tail())
    except Exception as e:
        print(f"FRED Error: {e}")

if __name__ == "__main__":
    test_fred()
