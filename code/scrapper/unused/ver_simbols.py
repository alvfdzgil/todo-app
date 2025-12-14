from ..symbols import obtener_ticker
from pandas import read_csv
import time
data=read_csv('../data/sp500.csv')
nombres=[]
for company in data['activo'].tolist():
    print(obtener_ticker(company))
    nombres.append(obtener_ticker(company))
    time.sleep(1)
data['Symbol']=nombres
data.to_csv('../data/sp500_con_simbolos.csv',index=False)