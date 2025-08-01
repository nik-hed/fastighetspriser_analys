
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import requests
import os
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from datetime import date
import urllib.request, json 

#https://github.com/kirajcg/pyscbwrapper/blob/master/pyscbwrapper.ipynb
from pyscbwrapper import SCB


market_colors = {
    'Dow Jones': 'black',
    'Länsförsäkringar Fastighetsfond': 'black',           
    'Sverige': 'red',
    'Stockholm': 'green',
    'Linköping': 'orange',
    'Örebro': 'pink',
    'Malmö': 'purple',
    'Göteborg': 'grey',
    'Norrköping': 'blue',
    'Västerås': 'brown',
    'Uppsala': 'violet'
}


def calculate_total_return(df,return_column):

    df['return'] = df[f'{return_column}'] / df[f'{return_column}'].shift(1)
    df.loc[0, 'return'] = 1
    df['total_return'] = df['return'].cumprod()


    return df


def convert_unix(df,selected_min_year,selected_max_year):

    """issue when fetching the data is that depending on the years different dates are fetched, in order to 
    correct this,the closest date to the first day of each year will get fetched
    after that the filtering will be done based on the user input"""

    df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.normalize()
    df['year'] = df['date'].dt.year
    df['days_from_jan1'] = (df['date'] - pd.to_datetime(df['year'].astype(str) + '-01-01')).abs()
    df = df.loc[df.groupby('year')['days_from_jan1'].idxmin()].drop(columns='days_from_jan1').reset_index()
    df['date'] = pd.to_datetime(df['year'].astype(str) + '-01-01')
    df=df.query(f"date >= '{selected_min_year}-01-01' and  date<='{selected_max_year}-01-01'").reset_index()
    df['year'] = df['year'].astype(int)

    return df


#Collect data:


url_maklarstatistik='https://www.maklarstatistik.se/omrade/riket/#/bostadsratter/arshistorik-prisutveckling'

# Get the path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Build full path to the Excel file
file_path_maklarstatistik= os.path.join(current_dir, 'svensk_ mäklarstatistik_bostadsrätter_streamlit.xlsx')

fastighetspriser_df=pd.read_excel(file_path_maklarstatistik)
fastighetspriser_df = fastighetspriser_df.rename(columns={ 'År': 'year','kr/kvm': 'price','Område': 'market'})

#Macro:

#Inflation:
scb = SCB('sv')
scb.go_down('PR')
scb.go_down('PR0101')
scb.go_down('PR0101G')
scb.go_down('KPIF')
inflation_url=scb.get_url()
KPIF_data=scb.get_data()
KPIF_output=KPIF_data['data']
KPIF_df = pd.DataFrame(KPIF_output, columns=['key', 'values'])
KPIF_df['yearmonth'] = KPIF_df['key'].apply(lambda x: x[0])
KPIF_df['yearmonth'] = KPIF_df['yearmonth'].str.replace('M', '', regex=False).astype(int)
KPIF_df['KPIF'] = KPIF_df['values'].apply(lambda x: x[2])
KPIF_df['KPIF'] = pd.to_numeric(KPIF_df['KPIF'], errors='coerce')
KPIF_df = KPIF_df.drop(columns=['values','key'])
KPIF_df['year'] = KPIF_df['yearmonth'] // 100
KPIF_df['yearmonth'] = pd.to_datetime(KPIF_df['yearmonth'].astype(str), format='%Y%m')
KPIF_df=KPIF_df.query("year>=1995")
#%%
#Interest rate:

#Styrräntans serie-ID:
seriesId='SECBREPOEFF'

api_key=st.secrets["api_keys"]["riksbanken_primary_key"]
url=f"https://api.riksbank.se/swea/v1/ObservationAggregates/SECBREPOEFF/M/1995-01-01?subscription-key={api_key}"


with urllib.request.urlopen(url) as urlriksbank:
    data_riksbank = json.load(urlriksbank)


styrranta_df=pd.DataFrame(data_riksbank)

styrranta_df['yearmonth'] = pd.to_datetime(styrranta_df['from']).dt.to_period('M').dt.to_timestamp()
styrranta_df['yearmonth'] = styrranta_df['yearmonth'].dt.date

styrranta_df = styrranta_df.rename(columns={ 'average': 'styrranta'})

styrranta_df=styrranta_df[['yearmonth','styrranta','year']]





# Sidebar filters
# In order to not hide the filters
st.sidebar.header("")

# Market checkbox filters
markets = sorted(fastighetspriser_df['market'].unique())
selected_markets = st.sidebar.multiselect("Välj städer att inkludera:", markets, default=markets)

# Year range filter
min_year = int(fastighetspriser_df['year'].min())
max_year = int(fastighetspriser_df['year'].max())

year_range = st.sidebar.slider(
"Välj vilka år att inkludera",
int(min_year),
int(max_year),
(int(min_year), int(max_year))
    )

############Fastighetspriser########################################################################


# Filter the DataFrame depending on the markets and the years.
fastighetspriser_df_filtered = fastighetspriser_df[
            (fastighetspriser_df['market'].isin(selected_markets)) &
            (fastighetspriser_df['year'] >= year_range[0]) &
            (fastighetspriser_df['year'] <= year_range[1])
        ]

st.header("Analys av fastighetspriser i Sverige", divider="gray")
st.subheader("Utveckling fastighetspriser i olika städer i Sverige")
fig, ax = plt.subplots()
for market in selected_markets:
    df_market = fastighetspriser_df_filtered[fastighetspriser_df_filtered['market'] == market]
    market_color = market_colors[f'{market}']
    ax.plot(df_market['year'], df_market['price'], label=market,color=market_color)

ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax.set_xlabel('År')
ax.set_ylabel('kr/kvm')
ax.legend()
ax.grid(True)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
plt.xlim(min(df_market['year']), max(df_market['year']))
if len(df_market)>=4:
    plt.xticks([df_market['year'].iloc[0],df_market['year'].iloc[len(df_market) // 4],df_market['year'].iloc[len(df_market) // 2],df_market['year'].iloc[len(df_market)-len(df_market) // 4] , df_market['year'].iloc[-1]])
else:
    plt.xticks([df_market['year'].iloc[0],df_market['year'].iloc[-1]])
st.pyplot(fig)        

selected_min_year, selected_max_year = year_range

fastighetspriser_df_filtered.loc['date'] = pd.to_datetime(fastighetspriser_df_filtered['year'].astype(str), format='%Y')


st.markdown("<u>Datakälla:</u>", unsafe_allow_html=True)

st.markdown(f"{url_maklarstatistik}")
st.markdown("""
Priserna som visar på marklarstistik.se är genomsnittet för året.
""")
st.markdown("---")
############Dow Jones########################################################################

st.subheader("Total avkastning Dow Jones mot fastighetspriser")

st.latex(r"""
\text{Total Avkastning}_t = \prod_{i=1}^{t} (\frac{P_{\text{i}}}{P_{\text{i-1}}}) 
""")

st.markdown("""
Där **i** är åren som väljs med "Välj vilka år att inkludera" och **P** är priset på index/fond/fastighet [1] under dessa år.
""")


#This adjustment is due to url not working for all years if 01-01 or 01-31 is chosen
#01-31 is chosen because for early years such as 1996 the first value if 1996-01-01 becomes 1995-12-31
url_dow_jones = f'https://www.avanza.se/_api/price-chart/stock/18985?from={selected_min_year}-01-31&to={selected_max_year}-12-31'
response = requests.get(url_dow_jones)
dow_jones = response.json()

series = dow_jones['ohlc']
dow_jones_df = pd.DataFrame(series)
dow_jones_df=convert_unix(dow_jones_df,selected_min_year,selected_max_year)
dow_jones_df=dow_jones_df.drop(columns=['open','low','high','totalVolumeTraded'])
dow_jones_df=calculate_total_return(dow_jones_df,'close')


fig, ax = plt.subplots()
for market in selected_markets:
    df_market = fastighetspriser_df_filtered[fastighetspriser_df_filtered['market'] == market]
    df_market=df_market.reset_index()
    df_market=calculate_total_return(df_market,'price') 
    market_color = market_colors[f'{market}']
    df_market = df_market.dropna(subset=['year'])
    df_market['year'] = df_market['year'].astype(int)
    ax.plot(df_market['year'], df_market['total_return'], label=market,color=market_color)



ax.plot(dow_jones_df['year'], dow_jones_df['total_return'], label='Dow Jones', color=market_colors['Dow Jones'])
ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax.set_xlabel('År')
ax.set_ylabel('Total avkastning')
ax.legend()
ax.grid(True)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
plt.xlim(min(dow_jones_df['year']), max(dow_jones_df['year']))
if len(dow_jones_df)>=4:
    plt.xticks([dow_jones_df['year'].iloc[0],dow_jones_df['year'].iloc[len(dow_jones_df) // 4],dow_jones_df['year'].iloc[len(dow_jones_df) // 2],dow_jones_df['year'].iloc[len(dow_jones_df)-len(dow_jones_df) // 4] , dow_jones_df['year'].iloc[-1]])
else:
    plt.xticks([dow_jones_df['year'].iloc[0],dow_jones_df['year'].iloc[-1]])
st.pyplot(fig)   

st.markdown("<u>Datakälla:</u>", unsafe_allow_html=True)
st.markdown(f"{url_dow_jones}")


st.markdown("---")

############Länsförsäkringar Fastighetsfond########################################################################


st.subheader("Total avkastning fastigheter med hävstång mot fastighetsfond")



inv_amount=1000
loan_amount=inv_amount/0.15


st.markdown(f"Beräkningen utgår ifrån att man har beloppet {inv_amount} att investera i en fastighetsfond [2] eller i en fastighet med hävstång ({inv_amount}/0.15). För fastigheten betalas hela lånet tillbaka, vilket inte är helt korrekt sedan amorteringskravet infördes.")

st.latex(r"""
\scriptsize         
\text{Total Avkastning med hävstång}_t = Lånebeloppet*(\prod_{i=1}^{t}\frac{P_{\text{i}}}{P_{\text{i-1}}} - 0.85) 
""")

url_fastighetsfond = f'https://www.avanza.se/_api/fund-guide/chart/350/{selected_min_year}-01-31/{selected_max_year}-12-31?raw=true'
response = requests.get(url_fastighetsfond)
fastighetsfond = response.json()


series = fastighetsfond['dataSerie']

# Convert to DataFrame
fastighetsfond_df = pd.DataFrame(series)
fastighetsfond_df = fastighetsfond_df.rename(columns={ 'x': 'timestamp'})
fastighetsfond_df=convert_unix(fastighetsfond_df,selected_min_year,selected_max_year)
fastighetsfond_df=calculate_total_return(fastighetsfond_df,'y')




fastighetsfond_df['total_return_hävstång'] = inv_amount * fastighetsfond_df['total_return']

fig, ax = plt.subplots()
for market in selected_markets:
    df_market = fastighetspriser_df_filtered[fastighetspriser_df_filtered['market'] == market]
    df_market=df_market.reset_index()
    df_market=calculate_total_return(df_market,'price')
    df_market = df_market.dropna(subset=['year'])
    df_market['total_return_hävstång'] = loan_amount * df_market['total_return'] - (loan_amount-inv_amount)
    market_color = market_colors[f'{market}']
    df_market['year'] = df_market['year'].astype(int)
    ax.plot(df_market['year'], df_market['total_return_hävstång'], label=market,color=market_color)



ax.plot(fastighetsfond_df['year'], fastighetsfond_df['total_return_hävstång'], label='Fastighetsfond', color=market_colors['Länsförsäkringar Fastighetsfond'])
ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax.set_xlabel('År')
ax.set_ylabel('Total avkastning med hävstång')
ax.legend()
ax.grid(True)
ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1))
plt.xlim(min(fastighetsfond_df['year']), max(fastighetsfond_df['year']))
if len(fastighetsfond_df)>=4:
    plt.xticks([fastighetsfond_df['year'].iloc[0],fastighetsfond_df['year'].iloc[len(fastighetsfond_df) // 4],fastighetsfond_df['year'].iloc[len(fastighetsfond_df) // 2],fastighetsfond_df['year'].iloc[len(fastighetsfond_df)-len(fastighetsfond_df) // 4] , fastighetsfond_df['year'].iloc[-1]])
else:
    plt.xticks([fastighetsfond_df['year'].iloc[0],fastighetsfond_df['year'].iloc[-1]])

st.pyplot(fig) 



st.markdown("<u>Datakälla:</u>", unsafe_allow_html=True)
st.markdown(f"{url_fastighetsfond}")
st.markdown("---")

#Makro

st.subheader("Makro(Styrränta och Inflation) och fastighetspriser")

st.markdown("***Styrränta:***")
st.markdown("Styrräntan är den ränta som Riksbankens direktion fattar beslut om i syfte att uppnå inflationsmålet. Styrräntans funktion och syfte är att styra dagslåneräntan på marknaden och påverka andra räntor i ekonomin så att inflationsmålet uppnås. [3]")

fig, ax = plt.subplots()
ax.plot(styrranta_df['yearmonth'], styrranta_df['styrranta'], label=['Styrränta'], color='black')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  
ax.set_xlabel("År")
ax.set_ylabel("Styrränta")
ax.set_title("Historisk utveckling av styrräntan")
ax.legend(loc='upper right', bbox_to_anchor=(1.6, 1))
ax.grid(True)
plt.xlim(min(styrranta_df['yearmonth']), max(styrranta_df['yearmonth']))
if len(styrranta_df)>=4:
    plt.xticks([styrranta_df['yearmonth'].iloc[0],styrranta_df['yearmonth'].iloc[len(styrranta_df) // 4],styrranta_df['yearmonth'].iloc[len(styrranta_df) // 2],styrranta_df['yearmonth'].iloc[len(styrranta_df)-len(styrranta_df) // 4] , styrranta_df['yearmonth'].iloc[-1]])
else:
    plt.xticks([styrranta_df['yearmonth'].iloc[0],styrranta_df['yearmonth'].iloc[-1]])

st.pyplot(fig)


st.markdown("<u>Datakälla:</u>", unsafe_allow_html=True)
st.markdown(f"https://www.riksbank.se/sv/statistik/rantor-och-valutakurser/sok-rantor-och-valutakurser/?s=g2-SECBREPOEFF&a=M&from=1995-01-02&to={date.today().strftime('%Y-%m-%d')}&fs=3#result-section")


st.markdown("---")

st.markdown("***Inflation(KBIF):***")
st.markdown("Inflationen visar hur prisnivån, mätt som KPIF, har förändrats jämfört med samma månad föregående år. Målet är att inflationen ska vara 2 procent per år, mätt som den årliga procentuella förändringen i KPIF. [4]")




fig, ax = plt.subplots()
#to limit the y-axis in the plot
ax.yaxis.set_major_locator(MaxNLocator(integer=True))
ax.plot(KPIF_df['yearmonth'], KPIF_df['KPIF'], label=['KPIF'], color='grey')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  # or '%Y' for just year
ax.set_xlabel("År")
ax.set_ylabel("KPIF")
ax.set_title("Historisk utveckling av inflationen")
ax.legend(loc='upper right', bbox_to_anchor=(1.6, 1))
ax.grid(True)
plt.xlim(min(KPIF_df['yearmonth']), max(KPIF_df['yearmonth']))
if len(KPIF_df)>=4:
    plt.xticks([KPIF_df['yearmonth'].iloc[0],KPIF_df['yearmonth'].iloc[len(KPIF_df) // 4],KPIF_df['yearmonth'].iloc[len(KPIF_df) // 2],KPIF_df['yearmonth'].iloc[len(KPIF_df)-len(KPIF_df) // 4] , KPIF_df['yearmonth'].iloc[-1]])
else:
    plt.xticks([KPIF_df['yearmonth'].iloc[0],KPIF_df['yearmonth'].iloc[-1]])

st.pyplot(fig)




st.markdown("<u>Datakälla:</u>", unsafe_allow_html=True)
#st.markdown("https://www.riksbank.se/sv/penningpolitik/inflationsmalet/inflationen-just-nu/")
st.markdown(f"{inflation_url}")

st.markdown("---")

st.markdown("För att enklare kunna jämföra fastighetspriser mot makro tas ett genomsnitt fram för varje år för inflationen och räntan, sen normaliseras(min-max normalization) [5] alla värden och visas därefter i samma figur:")


#used to compare to styrräntan:
styrranta_df_avg = styrranta_df.groupby('year')['styrranta'].mean().reset_index()
styrranta_df_avg.rename(columns={'styrranta': 'styrranta_y_avg'}, inplace=True)
KPIF_df_avg = KPIF_df.groupby('year')['KPIF'].mean().reset_index()
KPIF_df_avg.rename(columns={'KPIF': 'kpif_y_avg'}, inplace=True)

macro_compare_df=fastighetspriser_df_filtered.merge(styrranta_df_avg, on='year').merge(KPIF_df_avg, on='year')
#only use market=Sverige
macro_compare_df=macro_compare_df.query("market=='Sverige'")
macro_compare_df = macro_compare_df.sort_values('year').reset_index(drop=True)

normalized_df = macro_compare_df.copy()
for col in ['price', 'styrranta_y_avg','kpif_y_avg']:
    min_val = macro_compare_df[col].min()
    max_val = macro_compare_df[col].max()
    normalized_df[col] = (macro_compare_df[col] - min_val) / (max_val - min_val)
    
fig, ax = plt.subplots()

ax.plot(normalized_df['year'], normalized_df['price'], label='Fastighetspriser_Sverige', color=market_colors['Sverige'])
ax.plot(normalized_df['year'], normalized_df['styrranta_y_avg'], label='Styrränta', color='black')
ax.plot(normalized_df['year'], normalized_df['kpif_y_avg'], label='KBIF', color='grey')
ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))


ax.set_xlabel('År')
ax.set_ylabel('Normaliserade makrovärden')
ax.legend()
ax.grid(True)
ax.legend(loc='upper right', bbox_to_anchor=(1.6, 1))
plt.xlim(min(normalized_df['year']), max(normalized_df['year']))
if len(normalized_df)>=4:
    plt.xticks([normalized_df['year'].iloc[0],normalized_df['year'].iloc[len(normalized_df) // 4],normalized_df['year'].iloc[len(normalized_df) // 2],normalized_df['year'].iloc[len(normalized_df)-len(normalized_df) // 4] , normalized_df['year'].iloc[-1]])
else:
    plt.xticks([normalized_df['year'].iloc[0],normalized_df['year'].iloc[-1]])

st.pyplot(fig) 

st.markdown("[1] https://www.avanza.se/index/om-indexet.html/18985/dow-jones")
st.markdown("[2] https://doc.morningstar.com/Document/ea76022ed9e0403688422e3cdd2d1afd.msdoc/?key=b9f1f970e71ab35ebb8299a03a0117c2e3ebb292872b668ea92e3b8d3ba9b3e79a8a45e5a3afde3e")
st.markdown("[3] https://www.riksbank.se/sv/statistik/rantor-och-valutakurser/styrranta-in--och-utlaningsranta/")
st.markdown("[4] https://www.riksbank.se/sv/penningpolitik/inflationsmalet/inflationen-just-nu/")
st.markdown("[5] https://en.wikipedia.org/wiki/Feature_scaling#Rescaling_(min-max_normalization)")
