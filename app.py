import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import plotly.express as px
import re

# --- 1. SETUP ---
st.set_page_config(page_title="Lumina BI (Gemini Edition)", layout="wide")

# REPLACE THIS WITH YOUR GEMINI API KEY
GEMINI_API_KEY = "YOUR GEMINI API KEY"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. UI ---
st.title("✨ Lumina: AI Data Intelligence")
st.write("Using Gemini 1.5 Flash to analyze your data in seconds.")

# --- 3. SIDEBAR ---
uploaded_file = st.sidebar.file_uploader("Upload Business CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # Clean column names for SQL compatibility
    df.columns = [re.sub(r'\W+', '_', col).strip('_') for col in df.columns]
    
    # Create In-Memory SQL Database
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    df.to_sql('business_data', conn, index=False, if_exists='replace')
    st.sidebar.success("✅ Data Loaded!")
    st.sidebar.write("### Column Names detected:")
    st.sidebar.info(", ".join(df.columns))

    # --- 4. QUERY ---
    query_input = st.text_input("Ask your data a question (e.g., 'What are the total sales by region?')")

    if query_input:
        with st.spinner("Gemini is analyzing..."):
            try:
                # Part A: Text to SQL
                sql_prompt = f"""
                You are a SQL expert. Table 'business_data' has columns: {list(df.columns)}.
                Write a SQLite query to answer this: {query_input}.
                Return ONLY the raw SQL code. No markdown, no '```sql', no explanations.
                """
                sql_response = model.generate_content(sql_prompt)
                sql_query = sql_response.text.strip().replace('```sql', '').replace('```', '')
                
                # Run SQL and get results
                res_df = pd.read_sql_query(sql_query, conn)
                
                # Part B: Visualization Suggestion
                viz_prompt = f"""
                Based on these columns: {list(res_df.columns)}, suggest the best chart type: 'bar', 'line', or 'pie'.
                Return only the word.
                """
                viz_response = model.generate_content(viz_prompt)
                viz_type = viz_response.text.strip().lower()

                # --- 5. DISPLAY RESULTS ---
                st.divider()
                c1, c2 = st.columns([1, 2])
                
                with c1:
                    st.subheader("📋 Data Result")
                    st.dataframe(res_df, use_container_width=True)
                
                with c2:
                    st.subheader("📊 Visualization")
                    if len(res_df.columns) >= 2:
                        x_col = res_df.columns[0]
                        y_col = res_df.columns[1]
                        
                        if 'bar' in viz_type:
                            fig = px.bar(res_df, x=x_col, y=y_col, color=x_col, template="plotly_dark")
                        elif 'line' in viz_type:
                            fig = px.line(res_df, x=x_col, y=y_col, template="plotly_dark")
                        else:
                            fig = px.pie(res_df, names=x_col, values=y_col, template="plotly_dark")
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Query returned a single value. No chart needed.")

            except Exception as e:
                st.error(f"Analysis Error: {e}")
                st.code(sql_query if 'sql_query' in locals() else "Query generation failed")

else:
    st.info("Please upload a CSV file from the sidebar to begin.")
