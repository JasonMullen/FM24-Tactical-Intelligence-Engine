from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

st.set_page_config(
    page_title='FM24 Tactical Intelligence Engine',
    page_icon='?',
    layout='wide',
)

st.title('FM24 Tactical Intelligence Engine')

st.write(
    '''
    This is the first working version of the project.

    Current goal:
    - Upload FM24 player database
    - Clean the data
    - Search players
    - Build player role-fit scores
    - Later: add philosophy, opposition analysis, and tactical puzzle solving
    '''
)

uploaded_file = st.file_uploader(
    'Upload your FM24 player database',
    type=['csv', 'xlsx', 'xls', 'html', 'htm']
)

if uploaded_file is None:
    st.info('Upload your FM24 database file to begin.')
    st.stop()

try:
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.lower().endswith(('.html', '.htm')):
        tables = pd.read_html(uploaded_file)
        df = tables[0]
    else:
        st.error('Unsupported file type.')
        st.stop()

    df = df.dropna(axis=0, how='all')
    df = df.dropna(axis=1, how='all')
    df = df.drop_duplicates()
    df.columns = [str(col).strip() for col in df.columns]

    st.success(f'Loaded {len(df):,} rows and {len(df.columns):,} columns.')

    st.subheader('Detected Columns')
    st.write(list(df.columns))

    st.subheader('Player Database Preview')
    st.dataframe(df.head(100), use_container_width=True)

except Exception as error:
    st.error(f'Could not load file: {error}')
