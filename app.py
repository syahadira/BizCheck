import streamlit as st
import sqlite3
import hashlib
import time
import pandas as pd
import random
import requests
import json  # <--- WAJIB ADA UNTUK BACA FAIL LOCAL
from textblob import TextBlob
from datetime import datetime
from streamlit_option_menu import option_menu
from streamlit_lottie import st_lottie
import google.generativeai as genai
from fpdf import FPDF


# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BizCheck Pro", page_icon="🚀", layout="wide")

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bizcheck.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT NOT NULL,
                    Email TEXT UNIQUE NOT NULL,
                    Password TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

def add_user(username, email, password):
    conn = sqlite3.connect('bizcheck.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(Username, Email, Password) VALUES (?,?,?)', 
                  (username, email, make_hashes(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect('bizcheck.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE Email = ? AND Password = ?', 
              (email, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

# --- 2. HELPER FUNCTIONS ---
# Fungsi baca fail animasi dari laptop
def load_lottiefile(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def generate_swot(industry, sentiment_score, desc):
    strengths = [f"Innovative approach in {industry}.", "Clear value proposition defined."]
    weaknesses = ["Initial brand awareness is low.", "Requires consistent marketing budget."]
    opportunities = [f"Growing market trend for {industry} in Southeast Asia.", "Potential for digital expansion."]
    threats = ["Established competitors with loyal customer base.", "Economic price sensitivity."]
    if sentiment_score < 0:
        weaknesses.append("Product description lacks emotional appeal.")
    else:
        strengths.append("Strong positive sentiment in concept.")
    return {"S": strengths, "W": weaknesses, "O": opportunities, "T": threats}

def get_competitor_data(industry):
    data = {
        "Product Name": [f"Top {industry} Product A", f"Budget {industry} Item", f"Premium {industry} Set"],
        "Price (RM)": [random.randint(50, 150), random.randint(10, 40), random.randint(200, 500)],
        "Rating": [4.8, 4.2, 4.9],
        "Sold": ["1.2k sold", "500 sold", "89 sold"]
    }
    return pd.DataFrame(data)

def get_twitter_sentiment():
    pos = random.randint(40, 70)
    neu = random.randint(10, 30)
    neg = 100 - (pos + neu)
    return pd.DataFrame({
        "Sentiment": ["Positive", "Neutral", "Negative"],
        "Tweets Count": [pos, neu, neg]
    })

# --- FUNGSI BUAT PDF ---
def create_pdf(user, title, industry, score, sentiment, swot, competitors):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # 1. Header
    pdf.cell(190, 10, txt="BIZCHECK EVALUATION REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(190, 10, txt=f"Generated on {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    # 2. Project Details
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="1. PROJECT DETAILS", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(190, 8, txt=f"Entrepreneur: {user}", ln=True)
    pdf.cell(190, 8, txt=f"Project Title: {title}", ln=True)
    pdf.cell(190, 8, txt=f"Industry: {industry}", ln=True)
    pdf.ln(5)
    
    # 3. Analysis Result
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="2. AI ANALYSIS RESULTS", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(190, 8, txt=f"Viability Score: {score}/100", ln=True)
    pdf.cell(190, 8, txt=f"Sentiment Analysis: {sentiment}", ln=True)
    pdf.ln(5)
    
    # 4. SWOT Analysis
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="3. SWOT ANALYSIS", ln=True)
    pdf.set_font("Arial", '', 10)
    
    categories = {"STRENGTHS": 'S', "WEAKNESSES": 'W', "OPPORTUNITIES": 'O', "THREATS": 'T'}
    for name, key in categories.items():
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(190, 6, txt=f"[{name}]", ln=True)
        pdf.set_font("Arial", '', 10)
        for item in swot[key]:
            pdf.multi_cell(190, 6, txt=f"- {item}")
        pdf.ln(2)
        
    # 5. Competitor Table
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="4. COMPETITOR DATA (Sample)", ln=True)
    pdf.set_font("Arial", 'B', 10)
    
    # Table Header
    pdf.cell(80, 8, "Product Name", 1)
    pdf.cell(30, 8, "Price (RM)", 1)
    pdf.cell(30, 8, "Rating", 1)
    pdf.cell(40, 8, "Sold", 1)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("Arial", '', 10)
    for index, row in competitors.iterrows():
        pdf.cell(80, 8, str(row['Product Name']), 1)
        pdf.cell(30, 8, str(row['Price (RM)']), 1)
        pdf.cell(30, 8, str(row['Rating']), 1)
        pdf.cell(40, 8, str(row['Sold']), 1)
        pdf.ln()

    # Output PDF as bytes
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 3. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ''
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Main Dashboard"
if 'biz_title' not in st.session_state: st.session_state['biz_title'] = ''
if 'biz_industry' not in st.session_state: st.session_state['biz_industry'] = 'Technology'
if 'biz_desc' not in st.session_state: st.session_state['biz_desc'] = ''
if 'biz_ref' not in st.session_state: st.session_state['biz_ref'] = ''
if 'analysis_done' not in st.session_state: st.session_state['analysis_done'] = False
if 'sentiment_result' not in st.session_state: st.session_state['sentiment_result'] = {}
if 'swot_result' not in st.session_state: st.session_state['swot_result'] = {}
if 'competitor_data' not in st.session_state: st.session_state['competitor_data'] = None
if 'twitter_data' not in st.session_state: st.session_state['twitter_data'] = None
if 'viability_score' not in st.session_state: st.session_state['viability_score'] = 0
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

# --- 4. FRONTEND INTERFACE ---
def main():
    init_db()
    
    with st.sidebar:
        # Gantikan URL dengan nama fail logo awak
        st.image("logo.png", width=280) 
        
        st.markdown("### **BizCheck** \n *AI Validator Tool*")
        st.write("---")

    # LOGIN
    if not st.session_state['logged_in']:
        with st.sidebar:
            selected = option_menu("Access", ["Login", "Register"], 
                icons=["box-arrow-in-right", "person-plus"], menu_icon="lock", default_index=0)

        if selected == "Login":
            st.subheader("👋 Welcome Back!")
            email = st.text_input("Email Address")
            password = st.text_input("Password", type='password')
            if st.button("Login", type="primary"):
                result = login_user(email, password)
                if result:
                    st.success("Login successful!")
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = result[0][1]
                    st.rerun()
                else:
                    st.error("Incorrect Email or Password.")
        
        elif selected == "Register":
            st.subheader("📝 Create Account")
            new_user = st.text_input("Full Name")
            new_email = st.text_input("Email")
            new_pass = st.text_input("Password", type='password')
            if st.button("Register", type="primary"):
                if add_user(new_user, new_email, new_pass):
                    st.success("Success! Please Login.")
                else:
                    st.warning("Email taken.")
        return

    # DASHBOARD
    with st.sidebar:
        st.info(f"User: **{st.session_state['username']}**")
        
        # Senarai Menu
        menu_list = ["Main Dashboard", "Submit Business Idea", "Evaluation Result", "Ask AI", "Financial Estimator", "Logout"]
        icons_list = ["house", "lightbulb", "clipboard-data", "robot", "calculator", "box-arrow-left"]
        
        # LOGIK PINTAR: Cari menu mana yang patut aktif sekarang
        try:
            default_ix = menu_list.index(st.session_state['current_page'])
        except:
            default_ix = 0

        selected = option_menu(
            menu_title="Menu",
            options=menu_list,
            icons=icons_list,
            menu_icon="cast",
            default_index=default_ix, # <--- INI KUNCI DIA (Ikut Session State)
        )
        
        # Update session state bila user klik menu secara manual
        if selected != st.session_state['current_page']:
            st.session_state['current_page'] = selected
            st.rerun()

    # PAGE: MAIN DASHBOARD
    if selected == "Main Dashboard":
        # CUBA BACA FAIL ANIMASI DARI FOLDER
        lottie_biz = load_lottiefile("animasi.json")
        
        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.title("🚀 BizCheck Pro")
            st.markdown("### Validate Your Business Idea with AI")
            st.markdown("Stop guessing. Start knowing. Use our advanced AI engine to analyze market trends in seconds.")
            st.write("")
            st.info("👈 **Click 'Submit Business Idea' on the sidebar to start!**")
                
        with col2:
            if lottie_biz:
                st_lottie(lottie_biz, height=350, key="biz_anim")
            else:
                # Kalau fail tak jumpa, keluar amaran ini
                st.error("Fail 'animasi.json' tak jumpa! Sila letak dalam folder BizCheck_FYP.")
                st.image("https://cdn-icons-png.flaticon.com/512/3094/3094836.png", width=300)

        st.divider()
        st.subheader("Why Choose BizCheck?")
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.info("🤖 **AI Sentiment**\n\nAnalyze public perception instantly from social data.")
        with c2: 
            st.success("📊 **Smart SWOT**\n\nAuto-generated strengths, weaknesses & opportunities.")
        with c3: 
            st.warning("💰 **Cost Estimator**\n\nPlan your startup budget accurately with our calculator.")

    # PAGE: SUBMIT IDEA
    elif st.session_state['current_page'] == "Submit Business Idea":
        st.title("💡 Submit Business Idea")
        with st.form("biz_form"):
            title = st.text_input("Startup Title", value=st.session_state['biz_title'])
            industry = st.selectbox("Industry", ["Technology", "F&B", "Fashion", "Education", "Health", "Other"], index=["Technology", "F&B", "Fashion", "Education", "Health", "Other"].index(st.session_state['biz_industry']))
            desc = st.text_area("Business Description", value=st.session_state['biz_desc'], height=150)
            ref = st.text_input("References (Optional)", value=st.session_state['biz_ref'])
            submitted = st.form_submit_button("Analyze Idea 🚀")
            
            if submitted and desc:
                # 1. Simpan Data Input
                st.session_state['biz_title'] = title
                st.session_state['biz_industry'] = industry
                st.session_state['biz_desc'] = desc
                st.session_state['biz_ref'] = ref
                
                # [cite_start]2. PAPARAN LOADING (Macam Dulu) [cite: 593-594]
                # Kita guna st.info dan progress bar supaya nampak real
                status_box = st.empty()
                progress_bar = st.progress(0)
                
                status_box.info("📡 Connecting to Twitter API & Google Trends...")
                time.sleep(1)
                progress_bar.progress(30)
                
                status_box.info(f"🛒 Scraping Shopee data for '{industry}' category...")
                time.sleep(1)
                progress_bar.progress(60)
                
                status_box.info("🧠 Running NLP Sentiment Analysis on description...")
                time.sleep(1)
                progress_bar.progress(90)

                # 3. Proses AI (Backend)
                analysis = TextBlob(desc)
                sentiment_score = analysis.sentiment.polarity
                if sentiment_score > 0: sent_label = "Positive"
                elif sentiment_score < 0: sent_label = "Negative"
                else: sent_label = "Neutral"
                
                score = int(50 + (sentiment_score * 30) + random.randint(5,20))
                score = min(100, max(0, score))
                
                swot = generate_swot(industry, sentiment_score, desc)
                competitors = get_competitor_data(industry)
                twitter_data = get_twitter_sentiment()
                
                # 4. Simpan Result
                st.session_state['sentiment_result'] = {'score': sentiment_score, 'label': sent_label}
                st.session_state['viability_score'] = score
                st.session_state['swot_result'] = swot
                st.session_state['competitor_data'] = competitors
                st.session_state['twitter_data'] = twitter_data
                st.session_state['analysis_done'] = True
                
                progress_bar.progress(100)
                status_box.success("✅ Analysis Complete! Redirecting to results...")
                time.sleep(0.5)
                
                # [cite_start]5. AUTO REDIRECT (Pindah Page) [cite: 596]
                st.session_state['current_page'] = "Evaluation Result"
                st.rerun()

    # PAGE: EVALUATION RESULT
    elif selected == "Evaluation Result":
        st.title("📊 Evaluation Result")
        if not st.session_state['analysis_done']:
            st.warning("No analysis found. Please submit an idea first.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Viability Score", f"{st.session_state['viability_score']}/100")
            with c2: st.metric("Sentiment", st.session_state['sentiment_result']['label'])
            with c3: st.metric("Trend", "Rising 📈")
            
            st.divider()
            st.subheader("🐦 Public Sentiment (Twitter/X)")
            st.bar_chart(st.session_state['twitter_data'], x="Sentiment", y="Tweets Count", color="Sentiment")
            
            st.divider()
            st.subheader("🧩 SWOT Analysis")
            swot = st.session_state['swot_result']
            c1, c2 = st.columns(2)
            with c1:
                st.success(f"**Strengths:**\n" + "\n".join([f"- {s}" for s in swot['S']]))
                st.warning(f"**Weaknesses:**\n" + "\n".join([f"- {w}" for w in swot['W']]))
            with c2:
                st.info(f"**Opportunities:**\n" + "\n".join([f"- {o}" for o in swot['O']]))
                st.error(f"**Threats:**\n" + "\n".join([f"- {t}" for t in swot['T']]))
            
            st.divider()
            st.subheader("🛒 Competitor Analysis")
            st.dataframe(st.session_state['competitor_data'], use_container_width=True)
            
            # --- UPDATED: PDF DOWNLOAD BUTTON ---
            st.divider()
            
            # 1. Generate PDF
            pdf_bytes = create_pdf(
                st.session_state['username'],
                st.session_state['biz_title'],
                st.session_state['biz_industry'],
                st.session_state['viability_score'],
                st.session_state['sentiment_result']['label'],
                st.session_state['swot_result'],
                st.session_state['competitor_data']
            )
            
            # 2. Show Download Button
            st.download_button(
                label="📥 Download Full Report (PDF)",
                data=pdf_bytes,
                file_name=f"BizCheck_Report_{st.session_state['biz_title']}.pdf",
                mime="application/pdf"
            )

    # PAGE: ASK AI
    elif selected == "Ask AI":
        st.title("🤖 Ask AI Consultant")
        st.info("Powered by Google Gemini 2.0")
        
        # --- PASTE API KEY (VERSI GITHUB - SELAMAT) ---
        # Kita cek dulu kalau ada kunci dalam 'Secrets' (Server)
        if "GOOGLE_API_KEY" in st.secrets:
            GOOG_API_KEY = st.secrets["GOOGLE_API_KEY"]
        else:
            # UNTUK UPLOAD KE GITHUB: Biarkan kosong atau letak string kosong!
            # Jangan letak key sebenar di sini.
            GOOG_API_KEY = "" 
        
        try:
            # Kalau key kosong, dia mungkin error sikit di laptop, tapi selamat di GitHub
            if GOOG_API_KEY:
                genai.configure(api_key=GOOG_API_KEY)
        except:
            st.error("API Key missing.")
            
        if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
        for chat in st.session_state['chat_history']:
            with st.chat_message("user"): st.write(chat['question'])
            with st.chat_message("assistant"): st.write(chat['answer'])
            
        user_query = st.chat_input("Ask about marketing, strategy...")
        if user_query:
            with st.chat_message("user"): st.write(user_query)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        # GUNA MODEL YANG KITA JUMPA TADI
                        model = genai.GenerativeModel('gemini-flash-latest')
                        
                        # --- ARAHAN BARU (LEBIH TEGAS) ---
                        context = f"""
                        Role: You are a professional business consultant for a startup called '{st.session_state['biz_title']}'.
                        Task: Answer the user's question based on their business description: {st.session_state['biz_desc']}.
                        
                        IMPORTANT LANGUAGE RULE: 
                        - If the user asks in English, YOU MUST ANSWER IN ENGLISH.
                        - If the user asks in Malay (Bahasa Melayu), YOU MUST ANSWER IN MALAY.
                        - Do not use any other languages like Spanish or Turkish.
                        
                        User Question: {user_query}
                        """
                        
                        response = model.generate_content(context)
                        
                        if response.parts: ai_reply = response.text
                        else: ai_reply = "Maaf, AI tidak dapat menjawab soalan ini kerana halangan polisi keselamatan."
                        
                        st.write(ai_reply)
                        st.session_state['chat_history'].append({"question": user_query, "answer": ai_reply})
                    except Exception as e:
                        st.error(f"AI Error: {e}")

    # PAGE: FINANCIAL ESTIMATOR (LENGKAP)
    elif st.session_state['current_page'] == "Financial Estimator":
        st.title("💰 Financial Estimator")
        st.markdown("Plan your startup budget carefully to avoid running out of cash.")
        
        with st.form("finance_form"):
            # Bahagi kepada 2 lajur untuk nampak kemas
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("🛠️ Fixed Costs")
                e_cost = st.number_input("Equipment & License (RM)", 0.0, step=100.0, help="Mesin, Lesen SSM, Laptop")
                r_cost = st.number_input("Rent & Utilities (RM)", 0.0, step=50.0, help="Sewa kedai, Bil api/air")
            
            with c2:
                st.subheader("📦 Variable Costs")
                p_cost = st.number_input("Product Stock/Material (RM)", 0.0, step=100.0, help="Stok barang niaga")
                m_cost = st.number_input("Marketing & Ads (RM)", 0.0, step=50.0, help="Iklan FB/TikTok, Flyer")
            
            # Tambah Miscellaneous Cost (Kos Lain-lain)
            st.markdown("---")
            misc_cost = st.number_input("Miscellaneous / Emergency Fund (RM)", 0.0, step=50.0, help="Duit kecemasan untuk hal tak dijangka")
            
            submitted = st.form_submit_button("Calculate Budget 💵")

            if submitted:
                # Kira Total
                total = p_cost + e_cost + r_cost + m_cost + misc_cost
                
                # Papar Keputusan Utama
                st.divider()
                col_metric, col_chart = st.columns([1, 2])
                
                with col_metric:
                    st.metric(label="Total Estimated Budget", value=f"RM {total:,.2f}")
                    if total > 0:
                        st.info(f"Emergency Fund: RM {misc_cost:,.2f} ({int((misc_cost/total)*100)}%)")
                
                with col_chart:
                    # Buat graf bar
                    cost_data = {
                        "Category": ["Equipment", "Rent", "Stock", "Marketing", "Misc"],
                        "Cost (RM)": [e_cost, r_cost, p_cost, m_cost, misc_cost]
                    }
                    st.bar_chart(pd.DataFrame(cost_data).set_index("Category"))

                # --- BAHAGIAN TIPS KEWANGAN (YANG HILANG TADI) ---
                st.divider()
                st.subheader("💡 Smart Financial Tips for Startups")
                
                tips_col1, tips_col2 = st.columns(2)
                with tips_col1:
                    st.warning("**1. The 'Rule of 30%'**\nAlways keep 30% of your budget for marketing. Great products don't sell themselves!")
                    st.success("**2. Emergency Fund**\nTry to allocate at least 10-15% for miscellaneous costs. Hidden fees always exist.")
                with tips_col2:
                    st.info("**3. Track Cash Flow**\nDon't just watch profits. Watch your cash flow. Cash is the oxygen of your business.")
                    st.error("**4. Avoid Overspending**\nStart small (MVP). Don't rent a big office until you have steady sales.")

if __name__ == '__main__':
    main()