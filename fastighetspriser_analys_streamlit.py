

import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests


fastighetspriser_df=pd.read_excel(f'svensk_ mäklarstatistik_bostadsrätter_streamlit.xlsx')
fastighetspriser_df = fastighetspriser_df.rename(columns={ 'År': 'year','kr/kvm': 'price','Område': 'market'})

#To make sure that avanza data is always fetched
start_year=1996






# Sidebar filters
st.sidebar.header("Filters")

# Market checkbox filters
markets = sorted(fastighetspriser_df['market'].unique())
selected_markets = st.sidebar.multiselect("Välj regioner att inkludera: (Sverige, Stockholm, Malmö, Linköping, Örebro)", markets, default=markets)

# Year range filter
min_year = int(fastighetspriser_df['year'].min())
max_year = int(fastighetspriser_df['year'].max())



year_range = st.sidebar.slider(
"Välj vilka år att inkludera",
int(min_year),
int(max_year),
(int(min_year), int(max_year))
    )



selected_market_analysis = st.sidebar.selectbox("Jämför fastighetsmarknad mot aktier/fonder", markets)

# Filter the DataFrame
df_filtered = fastighetspriser_df[
            (fastighetspriser_df['market'].isin(selected_markets)) &
            (fastighetspriser_df['year'] >= year_range[0]) &
            (fastighetspriser_df['year'] <= year_range[1])
        ]

# Plotting
st.subheader("Utveckling fastighetspriser i olika regioner i Sverige")
fig, ax = plt.subplots()
for market in selected_markets:
    df_market = df_filtered[df_filtered['market'] == market]
    ax.plot(df_market['year'], df_market['price'], label=market)

ax.set_xlabel('År')
ax.set_ylabel('kr/kvm')
ax.legend()
ax.grid(True)
st.pyplot(fig)        

selected_min_year, selected_max_year = year_range


st.text_area(" Källa: https://www.maklarstatistik.se/omrade/riket/#/bostadsratter/arshistorik-prisutveckling")



df_filtered=df_filtered.query(f"market=='{selected_market_analysis}'").reset_index()


df_filtered = df_filtered.dropna()



df_filtered['return'] = df_filtered['price'] / df_filtered['price'].shift(1)
df_filtered.loc[0, 'return'] = 1
df_filtered['total_return'] = df_filtered['return'].cumprod()

#This adjustment is due to url not working for all years if 01-01 or 01-31 is chosen
url_dow_jones = f'https://www.avanza.se/_api/price-chart/stock/18985?from={start_year}-01-01&to={selected_max_year}-12-31'
response = requests.get(url_dow_jones)
dow_jones = response.json()

series = dow_jones['ohlc']


dow_jones_df = pd.DataFrame(series)

dow_jones_df['date'] = pd.to_datetime(dow_jones_df['timestamp'], unit='ms').dt.strftime('%Y%m%d')

#This adjustment is due to url not working for all years if 01-01 or 01-31 is chosen
dow_jones_df= dow_jones_df[dow_jones_df['date'].str.endswith('1231')]

dow_jones_df['year'] = dow_jones_df['date'].str[:4].astype(int)

dow_jones_df=dow_jones_df.query(f"year>={selected_min_year-1}").reset_index()

dow_jones_df=dow_jones_df.drop(columns=['timestamp','open','low','high','totalVolumeTraded'])


dow_jones_df['return'] = dow_jones_df['close'] / dow_jones_df['close'].shift(1)
dow_jones_df.loc[0, 'return'] = 1

#Adjusted year
dow_jones_df['year'] = dow_jones_df['year']+1

dow_jones_df['total_return'] = dow_jones_df['return'].cumprod()


st.subheader("Total avkastning Dow jones mot Fastighetspriser")

fig = plt.figure()

for frame in [dow_jones_df,df_filtered]:
    plt.plot(frame['year'], frame['total_return'])
    plt.xlabel('År')
    plt.ylabel('Total avkastning')


plt.legend(['Dow jones',f'Fastighetspriser_{selected_market_analysis}'])

st.pyplot(fig)

st.text_area(f"Källa:{url_dow_jones}")
