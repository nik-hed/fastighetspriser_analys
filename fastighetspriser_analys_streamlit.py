
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import requests
import os
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

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
file_path_styrranta = os.path.join(current_dir, 'riksbank_styrranta_streamlit.xlsx')
styrranta_df=pd.read_excel(file_path_styrranta)
styrranta_df = styrranta_df.rename(columns={ 'Period': 'yearmonth','Medel': 'styrranta'})
styrranta_df['year'] = styrranta_df['yearmonth'] // 100  # Integer division to get the year
styrranta_df['yearmonth'] = pd.to_datetime(styrranta_df['yearmonth'].astype(str), format='%Y%m')
styrranta_df['styrranta'] = pd.to_numeric(styrranta_df['styrranta'], errors='coerce')

def calculate_total_return(df,return_column):

    df['return'] = df[f'{return_column}'] / df[f'{return_column}'].shift(1)
    df.loc[0, 'return'] = 1
    df['total_return'] = df['return'].cumprod()


    return df

#might be used later
def calculate_cumulative_return(df,return_column):

    df['cumulative_return'] = df[f'{return_column}'] / df[f'{return_column}'].iloc[0]

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
st.pyplot(fig)        

selected_min_year, selected_max_year = year_range

fastighetspriser_df_filtered['date'] = pd.to_datetime(fastighetspriser_df_filtered['year'].astype(str), format='%Y')

st.markdown("**Källa:**") 
st.markdown(f"{url_maklarstatistik}")
st.markdown("""
Priserna som visar på marklarstistik.se är genomsnittet för året.
""")

############Dow Jones########################################################################

st.subheader("Total avkastning Dow jones mot Fastighetspriser")

st.latex(r"""
\text{Total Avkastning}_t = \prod_{i=1}^{t} (\frac{P_{\text{i}}}{P_{\text{i-1}}}) 
""")

st.markdown("""
Där **i** är åren som väljs med "Välj vilka år att inkludera" och **P** är priset på index/fond/fastighet under dessa år.
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
st.pyplot(fig)   

st.markdown("**Källor:**")
st.markdown(f"{url_dow_jones}")
st.markdown("https://www.avanza.se/index/om-indexet.html/18985/dow-jones")



############Länsförsäkringar Fastighetsfond########################################################################


st.subheader("Total avkastning fastigheter med hävstång mot fastighetsfond")

url_fastighetsfond = f'https://www.avanza.se/_api/fund-guide/chart/350/{selected_min_year}-01-31/{selected_max_year}-12-31?raw=true'
response = requests.get(url_fastighetsfond)
fastighetsfond = response.json()


series = fastighetsfond['dataSerie']

# Convert to DataFrame
fastighetsfond_df = pd.DataFrame(series)
fastighetsfond_df = fastighetsfond_df.rename(columns={ 'x': 'timestamp'})
fastighetsfond_df=convert_unix(fastighetsfond_df,selected_min_year,selected_max_year)
fastighetsfond_df=calculate_total_return(fastighetsfond_df,'y')



#might add for the user to change this
inv_amount=1000
loan_amount=inv_amount/0.15

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



ax.plot(fastighetsfond_df['year'], fastighetsfond_df['total_return_hävstång'], label='Länsförsäkringar Fastighetsfond', color=market_colors['Länsförsäkringar Fastighetsfond'])
ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax.set_xlabel('År')
ax.set_ylabel('Total avkastning med hävstång')
ax.legend()
ax.grid(True)
ax.legend(loc='upper right', bbox_to_anchor=(1.6, 1))
st.pyplot(fig) 

st.markdown(f"Beräkningen utgår ifrån att man har beloppet {inv_amount} att investera i en fastighetsfond eller i en fastighet mha lånebeloppet={inv_amount}/0.15(Hävstång). För fastigheten betalas hela lånet tillbaka, vilket inte är helt korrekt sedan amorteringskravet infördes.")

st.latex(r"""
\scriptsize         
\text{Total Avkastning med hävstång}_t = Lånebeloppet*(\prod_{i=1}^{t}\frac{P_{\text{i}}}{P_{\text{i-1}}} - 0.85) 
""")

st.markdown("**Källor:**")
st.markdown(f"{url_fastighetsfond}")
st.markdown("https://doc.morningstar.com/Document/ea76022ed9e0403688422e3cdd2d1afd.msdoc/?key=b9f1f970e71ab35ebb8299a03a0117c2e3ebb292872b668ea92e3b8d3ba9b3e79a8a45e5a3afde3e")
#Makro

st.subheader("Makro(Styrränta och Inflation) och Fastighetspriser")

st.markdown("**Styrränta**")
st.markdown("Styrränta är den ränta som bankerna kan låna eller placera till i Riksbanken på sju dagar. Riksbankens ränta är Riksbankens viktigaste styrränta.Riksbankens styrränta kallades reporänta fram till 8 juni 2022")
st.markdown("**Källa:**")
st.markdown("https://www.riksbank.se/sv/statistik/rantor-och-valutakurser/sok-rantor-och-valutakurser/?s=g2-SECBREPOEFF&a=M&from=1995-01-02&to=2025-06-17&fs=3#result-section")


fig, ax = plt.subplots()
ax.plot(styrranta_df['yearmonth'], styrranta_df['styrranta'], label=['Styrränta'], color='blue')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  
ax.set_xlabel("År")
ax.set_ylabel("Styrränta")
ax.set_title("Historisk utveckling av styrräntan")
ax.legend(loc='upper right', bbox_to_anchor=(1.6, 1))
ax.grid(True)

st.pyplot(fig)

st.markdown("**Inflation:**")
st.markdown("Inflationen visar hur prisnivån, mätt som KPIF, har förändrats jämfört med samma månad föregående år. Målet är att inflationen ska vara 2 procent per år, mätt som den årliga procentuella förändringen i KPIF.")
st.markdown("**Källa:**")
st.markdown("https://www.riksbank.se/sv/penningpolitik/inflationsmalet/inflationen-just-nu/")


fig, ax = plt.subplots()
#to limit the y-axis in the plot
ax.yaxis.set_major_locator(MaxNLocator(integer=True))
ax.plot(KPIF_df['yearmonth'], KPIF_df['KPIF'], label=['KPIF'], color='red')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))  # or '%Y' for just year
ax.set_xlabel("År")
ax.set_ylabel("KPIF")
ax.set_title("Historisk utveckling av inflationen")
ax.legend(loc='upper right', bbox_to_anchor=(1.6, 1))
ax.grid(True)

st.pyplot(fig)



st.markdown("För att enklare kunna jämföra fastighetspriser mot makro tas ett genomsnitt fram för varje år för inflationen och räntan, sen normaliseras alla värdena och visas därefter i samma figur nedan.")
st.markdown("Normalisering av värden är i detta fall: https://en.wikipedia.org/wiki/Feature_scaling#Rescaling_(min-max_normalization)")


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
st.pyplot(fig)