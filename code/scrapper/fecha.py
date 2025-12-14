import yfinance as yf
import datetime as datetime
import calendar

def fechas_unix(symbol):
    ticker = yf.Ticker(symbol)
    expirations = ticker.options 
    
    result = []
    for s in expirations:
        d = datetime.datetime.strptime(s, "%Y-%m-%d")
        ts = calendar.timegm(d.timetuple()) 
        result.append({"date": s, "timestamp": ts})
    return result

if __name__ == "__main__":
    for item in fechas_unix("NVDA"):
        print(item["date"], "→", item["timestamp"])
