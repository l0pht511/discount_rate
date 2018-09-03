# -*- coding: utf-8 -*-
"""
Spyderエディタ

これは一時的なスクリプトファイルです
"""
import datetime
import pandas as pd
import math
import numpy as np
from scipy import optimize
from dateutil.relativedelta import relativedelta

def fwrd(df_s, df_e, strt, end):
    return (df_s / df_e -1) * 360 / (end - strt) 


Capital = 100000000
spot_days = 4
value_date = datetime.date(2018, 8, 31)

df_jpl = pd.read_csv('input/JPYLIBOR.csv',
                     parse_dates =['Start date', 'Maturity'],
                     index_col='Maturuty_name')



print(df_jpl)



#jpy_spot = df_jpl.at[0, 'dsrate']
#print(spam)

print(df_jpl.dtypes)

df_jpl['day_difference'] = (df_jpl['Maturity'] - df_jpl['Start date']).apply(lambda x: x.days)

df_jpl['dsf_jpy'] = 1.0

dsf_sn_spot = 1 / (1 + (df_jpl.at['S/N', 'Market quote']/100) * (1 / 360))
z_spot = -365 * math.log(dsf_sn_spot)
dsf_spot = math.exp(-1 * z_spot * 4 / 365)#要改良
dsf_sn = dsf_sn_spot * dsf_spot

df_jpl.at['S/N', 'dsf_jpy'] = dsf_sn

df_jpl.loc['1W':'1Y', 'dsf_jpy'] = dsf_spot / (1 + df_jpl['Market quote']/100 * df_jpl['day_difference'] / 360)

print(df_jpl)
#day_difference = (df_jpl["Maturity"]-df_jpl["Start date"]).apply(lambda x: x.days)

print(df_jpl.dtypes)

print(dsf_sn)

df_jpl['dsr_jpy'] = np.log(df_jpl['dsf_jpy'])* -365/(spot_days + (df_jpl['Maturity'] - df_jpl['Start date']).apply(lambda x :x.days)) 


print(df_jpl)


df_jpswap = pd.DataFrame({'Payment date': [df_jpl.at['6M', 'Maturity'] + relativedelta(months=i*6) for i in range(60)]})

df_jpswap['day_difference'] = (df_jpswap['Payment date'] - df_jpl.at['S/N', 'Start date']).apply(lambda x: x.days)

df_jpswap['dsrate'] = np.interp(df_jpswap['day_difference'], df_jpl['day_difference'], df_jpl['dsr_jpy'])

df_jpswap['dsf'] = np.exp(-1 * (df_jpswap['day_difference'] + spot_days) * df_jpswap['dsrate'] / 365)

df_jpswap['float_leg'] = 1.0
df_jpswap.at[0, 'float_leg'] = Capital * df_jpl.at['6M', 'Market quote'] / 100 * df_jpswap.at[0, 'day_difference'] / 360
df_jpswap.at[1, 'float_leg'] = Capital * fwrd(df_jpswap.at[0, 'dsf'], df_jpswap.at[1, 'dsf'], df_jpswap.at[0, 'day_difference'], df_jpswap.at[1, 'day_difference']) * (df_jpswap.at[1, 'day_difference'] - df_jpswap.at[0, 'day_difference'])  / 360

for i in range(59):
    df_jpswap.at[i+1, 'float_leg'] = Capital * fwrd(df_jpswap.at[i, 'dsf'], df_jpswap.at[i+1, 'dsf'], df_jpswap.at[i, 'day_difference'], df_jpswap.at[i+1, 'day_difference']) * (df_jpswap.at[i+1, 'day_difference'] - df_jpswap.at[i, 'day_difference'])  / 360

def npv(df, n, fixed, dsf=df_jpswap['dsf'], float_leg=df_jpswap['float_leg'], day_difference=df_jpswap['day_difference'], dsrate = df_jpswap['dsrate']):
    float_pv = 0
    fixed_pv = 0
    if n == 2 or n == 3:
        for i in range(n):
            float_pv += dsf[i] * float_leg[i]
        float_pv += df * Capital * fwrd(dsf[n-1], df, day_difference[n-1], day_difference[n]) * (day_difference[n] - day_difference[n-1]) / 360
        for i in range(n):
            if i == 0:
                fixed_pv += dsf[i] * Capital * fixed / 100 * day_difference[0] / 365
            else:
                fixed_pv += dsf[i] * Capital * fixed / 100 * (day_difference[i] - day_difference[i-1])  / 365
        fixed_pv += df * Capital * fixed / 100 * (day_difference[n] - day_difference[n-1]) / 365
    
        return float_pv - fixed_pv
    if n in [5, 7, 9, 11, 13, 15, 17, 19]:
        dsf.at[n] = df
        dsrate.at[n] = np.log(df) * -365/(day_difference[n] + spot_days)
        dsrate.at[n-1] = np.interp(day_difference[n-1], day_difference, dsrate)
        dsf.at[n-1] = np.exp(-1 * (day_difference[n-1] + spot_days) * dsrate[n-1] /365)
        for i in range(n-1):
            float_pv += dsf[i] * float_leg[i]
        float_pv += dsf[n-1] * Capital * fwrd(dsf[n-2], dsf[n-1], day_difference[n-2], day_difference[n-1]) * (day_difference[n-1] - day_difference[n-2]) / 360
        float_pv += df * Capital * fwrd(dsf[n-1], df, day_difference[n-1], day_difference[n]) * (day_difference[n] - day_difference[n-1]) / 360
        
        for i in range(n+1):
            if i == 0:
                fixed_pv += dsf.at[i] * Capital * fixed / 100 * day_difference[0] / 365
            else:
                fixed_pv += dsf[i] * Capital * fixed / 100 * (day_difference[i] - day_difference[i-1])  / 365
        return float_pv - fixed_pv
    if n == 23:
        dsf.at[n] = df
        dsrate.at[n] = np.log(df) * -365/(day_difference[n] + spot_days)
        dsrate_forint = dsrate.loc[:19]
        dsrate_forint.at[20] = dsrate.at[n]
        day_difference_forint = day_difference.loc[:19]
        day_difference_forint.at[20] = day_difference.at[n]
        for k in range(23-19):
            dsrate.at[20+k] = np.interp(day_difference[20+k], day_difference_forint, dsrate_forint)
            dsf.at[20+k] = np.exp(-1 * (day_difference[20+k] + spot_days) * dsrate[20+k] /365)
            float_leg.at[20+k] = Capital * fwrd(dsf.at[19+k], dsf.at[20+k], day_difference.at[19+k], day_difference.at[20+k]) * (day_difference.at[20+k] - day_difference.at[19+k])  / 360
        for i in range(n):
            float_pv += dsf[i] * float_leg[i]
        float_pv += df * Capital * fwrd(dsf[n-1], df, day_difference[n-1], day_difference[n]) * (day_difference[n] - day_difference[n-1]) / 360
        for i in range(n):
            if i == 0:
                fixed_pv += dsf[i] * Capital * fixed / 100 * day_difference[0] / 365
            else:
                fixed_pv += dsf[i] * Capital * fixed / 100 * (day_difference[i] - day_difference[i-1])  / 365
        fixed_pv += df * Capital * fixed / 100 * (day_difference[n] - day_difference[n-1]) / 365
        return float_pv - fixed_pv
    if n == 29:
        dsf.at[n] = df
        dsrate.at[n] = np.log(df) * -365/(day_difference[n] + spot_days)
        dsrate_forint = dsrate.loc[:23]
        dsrate_forint.at[24] = dsrate.at[n]
        day_difference_forint = day_difference.loc[:23]
        day_difference_forint.at[24] = day_difference.at[n]
        for k in range(5):
            dsrate.at[24+k] =np.interp(day_difference[24+k], day_difference_forint, dsrate_forint)
            dsf.at[24+k] = np.exp(-1 * (day_difference[24+k] + spot_days) * dsrate[24+k] /365)
            float_leg.at[24+k] = Capital * fwrd(dsf.at[23+k], dsf.at[24+k], day_difference.at[23+k], day_difference.at[24+k]) * (day_difference.at[24+k] - day_difference.at[23+k])  / 360
        for i in range(n):
            float_pv += dsf[i] * float_leg[i]
        float_pv += df * Capital * fwrd(dsf[n-1], df, day_difference[n-1], day_difference[n]) * (day_difference[n] - day_difference[n-1]) / 360
        for i in range(n):
            if i == 0:
                fixed_pv += dsf[i] * Capital * fixed / 100 * day_difference[0] / 365
            else:
                fixed_pv += dsf[i] * Capital * fixed / 100 * (day_difference[i] - day_difference[i-1])  / 365
        fixed_pv += df * Capital * fixed / 100 * (day_difference[n] - day_difference[n-1]) / 365
        return float_pv - fixed_pv
    
    if n in [39, 49, 59]:
        dsf.at[n] = df
        dsrate.at[n] = np.log(df) * -365/(day_difference[n] + spot_days)
        dsrate_forint = dsrate.loc[:n-10]
        dsrate_forint.at[n-9] = dsrate.at[n]
        day_difference_forint = day_difference.loc[:n-10]
        day_difference_forint.at[n-9] = day_difference.at[n]
        for k in range(9):
            dsrate.at[n-9+k] = np.interp(day_difference[n-9+k], day_difference_forint, dsrate_forint)
            dsf.at[n-9+k] = np.exp(-1 * (day_difference[n-9+k] + spot_days) * dsrate[n-9+k] /365)
            float_leg.at[n-9+k] = Capital * fwrd(dsf.at[n-10+k], dsf.at[n-9+k], day_difference.at[n-10+k], day_difference.at[n-9+k]) * (day_difference.at[n-9+k] - day_difference.at[n-10+k])  / 360
        for i in range(n):
            float_pv += dsf[i] * float_leg[i]
        float_pv += df * Capital * fwrd(dsf[n-1], df, day_difference[n-1], day_difference[n]) * (day_difference[n] - day_difference[n-1]) / 360
        for i in range(n):
            if i == 0:
                fixed_pv += dsf[i] * Capital * fixed / 100 * day_difference[0] / 365
            else:
                fixed_pv += dsf[i] * Capital * fixed / 100 * (day_difference[i] - day_difference[i-1])  / 365
        fixed_pv += df * Capital * fixed / 100 * (day_difference[n] - day_difference[n-1]) / 365
        return float_pv - fixed_pv



spam = npv(1, 2, df_jpl.at['18M', 'Market quote'], df_jpswap['dsf'], df_jpswap['float_leg'],)

print(spam)

print(df_jpswap)
for j in range(15):
    if j in [0, 1]:
        df_jpl.iloc[7+j, 4] = optimize.newton(npv, 1, args=(j+2, df_jpl.iloc[7+j, 2]))
        df_jpswap.at[2+j, 'dsf'] = df_jpl.iloc[7+j, 4]
    elif 1 < j < 10:
        df_jpl.iloc[7+j, 4] = optimize.newton(npv, 1, args=(2*j+1, df_jpl.iloc[7+j, 2]))
        df_jpswap.at[2*j+1, 'dsf'] = df_jpl.iloc[7+j, 4]
    elif j == 10:
        df_jpl.iloc[7+j, 4] = optimize.newton(npv, 1, args=(2*j+3, df_jpl.iloc[7+j, 2]))
        df_jpswap.at[2*j+3, 'dsf'] = df_jpl.iloc[7+j, 4]
    else:
        df_jpl.iloc[7+j, 4] = optimize.newton(npv, 1, args=(10*(j-8)-1, df_jpl.iloc[7+j, 2]))
        df_jpswap.at[10*(j-8)-1, 'dsf'] = df_jpl.iloc[7+j, 4]
    for i in range(59):
        df_jpswap.at[i+1, 'float_leg'] = Capital * fwrd(df_jpswap.at[i, 'dsf'], df_jpswap.at[i+1, 'dsf'], df_jpswap.at[i, 'day_difference'], df_jpswap.at[i+1, 'day_difference']) * (df_jpswap.at[i+1, 'day_difference'] - df_jpswap.at[i, 'day_difference'])  / 360
    df_jpl['dsr_jpy'] = np.log(df_jpl['dsf_jpy'])* -365/(spot_days + (df_jpl['Maturity'] - df_jpl['Start date']).apply(lambda x :x.days))
    df_jpswap['dsrate'] = np.interp(df_jpswap['day_difference'], df_jpl['day_difference'], df_jpl['dsr_jpy'])
    df_jpswap['dsf'] = np.exp(-1 * (df_jpswap['day_difference'] + spot_days) * df_jpswap['dsrate'] / 365)
print(df_jpswap)
print(df_jpl)