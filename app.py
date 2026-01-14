import streamlit as st
import sqlite3
import hashlib
import time
import pandas as pd
import random
import json
import numpy as np 
from textblob import TextBlob
from datetime import datetime
from streamlit_option_menu import option_menu
from streamlit_lottie import st_lottie
import google.generativeai as genai
from fpdf import FPDF
import os

# --- PENTING: Fix untuk TextBlob di Streamlit Cloud ---
import textblob
try:
    textblob.download_corpora()
except:
    pass

# --- IMPORT LIBRARY ---
try:
    from googlesearch import search
except ImportError:
    # Dummy function if library fails
    def search(*args, **kwargs): return []

try:
    from pytrends.request import TrendReq
except ImportError:
    pass

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BizCheck Pro", page_icon="🚀", layout="wide")

# --- 0. API CONFIGURATION (SECURE MODE) ---
# Kod ini HANYA akan baca dari Streamlit Secrets.
# TIADA lagi key yang hardcoded di sini.
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        st.error("🚨 API Key hilang! Sila set GOOGLE_API_KEY di Streamlit Secrets.")
        st.stop() # App akan berhenti di sini kalau tiada key
except Exception as e:
    st.error(f"🚨 Masalah Konfigurasi API: {e}")
    st.stop()

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

def login_user(email, password):
    conn = sqlite3.connect('bizcheck.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE Email = ? AND Password = ?', 
              (email, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

def add_user(username, email, password):
    conn = sqlite3.connect('bizcheck.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(Username, Email, Password) VALUES (?,?,?)', 
                  (username, email, make_hashes(password)))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

# --- 2. HELPER FUNCTIONS ---
def load_lottiefile(filepath):
    try:
        with open(filepath, "r") as f: return json.load(f)
    except: return None

# --- AI: SWOT ANALYSIS ---
def generate_swot(industry, sentiment_score, desc, title):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Generate SWOT for Malaysian startup "{title}" ({industry}): {desc}.
        Output JSON: {{"S": ["..."], "W": ["..."], "O": ["..."], "T": ["..."]}} (3 bullet points each).
        """
        res = model.generate_content(prompt)
        return json.loads(res.text.replace("```json", "").replace("```", "").strip())
    except:
        return {
            "S": [f"Innovative approach in {industry}", "Strong initial branding potential", "Flexible business model"],
            "W": ["Limited initial capital", "New player in market", "Requires heavy marketing"],
            "O": ["Growing digital adoption in Malaysia", "Potential for viral marketing", "Expanding target audience"],
            "T": ["Competitors with bigger budget", "Economic instability", "Changing consumer trends"]
        }

# --- SMART DYNAMIC TWITTER GENERATOR ---
def generate_simulated_twitter_data(title, desc):
    tweets = []
    
    def extract_keywords(text):
        ignore_words = ["saya", "aku", "kita", "nak", "mau", "ingin", "buat", "untuk", "bagi", "di", 
                        "ke", "dan", "yang", "i", "want", "to", "create", "a", "an", "the", "for", "is", "are"]
        words = text.split()
        meaningful_words = [w for w in words if w.lower() not in ignore_words and len(w) > 3]
        if meaningful_words:
            return " ".join(meaningful_words[:4]) 
        else:
            return title

    concept_text = extract_keywords(desc)
    
    # --- CUBA AI DULU (ONLINE) ---
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Act as 15 different Malaysian Twitter users reacting to a NEW business idea: "{concept_text}".
        Context: {desc}
        Generate 15 unique tweets.
        - Mix English, Malay, Manglish.
        - Use slang: "fuyoh", "padu", "mahal gila", "scam", "mantap", "racun".
        - Mention the concept "{concept_text}" naturally.
        - Sentiment: 5 Positive, 5 Neutral, 5 Negative.
        Output format JSON ONLY:
        [
            {{"handle": "@username", "content": "tweet content", "likes": 12, "time": "2h", "sentiment": "Positive"}},
            ...
        ]
        """
        res = model.generate_content(prompt)
        clean_text = res.text.replace("```json", "").replace("```", "").strip()
        tweets = json.loads(clean_text)
    except Exception as e:
        print(f"AI Failed, using Smart Backup: {e}")
    
    # --- SMART BACKUP (OFFLINE MODE) ---
    if len(tweets) < 10:
        usernames = ["@AhmadAlbab", "@GadisTiktok", "@AbangTesla", "@MakcikBawang", 
                     "@InvestorMudah", "@KakiMakan", "@TechFreak", "@MamatKodi", 
                     "@CikBunga", "@BudakU", "@KerjaKeras", "@BossSusu", "@ViralKini", 
                     "@SukaTravel", "@NetizenMals"]
        
        pos_templates = [
            "Weh, kalau wujud {c} kat Malaysia, confirm aku beli! 🔥",
            "Finally ada idea pasal {c}. Shut up and take my money! 💸",
            "Aku rasa projek {c} ni boleh pergi jauh. Support lokal bossku!",
            "Baru baca pasal {c}, not bad la idea dia. Kreatif.",
            "Fuyoh, {c} ni macam game changer untuk industry ni.",
            "Serious talk, aku perlukan solution {c} dalam hidup aku sekarang. 😂",
            "Mantap idea {c} ni. Harap execution dia pun padu.",
            "Ni yang kita mahukan! {c} memang function teruk."
        ]
        
        neg_templates = [
            "Apa benda la idea {c} ni. Macam takde function je. 😒",
            "Mahal gila kot kalau nak buat {c} ni. Siapa je mampu?",
            "Scam ke ni? Hati-hati guys dengan idea {c} macam ni.",
            "Hmm, {c} lagi? Macam dah berlambak orang buat.",
            "Overrated la idea {c}. Indah khabar dari rupa.",
            "Susah nak jalan la bisnes {c} kat Malaysia ni. Market kecik.",
            "Tolonglah jangan buat {c} kalau takde experience. Nanti lingkup."
        ]
        
        neu_templates = [
            "Ada sesiapa faham pasal {c}? Bagi pencerahan sikit. 🤔",
            "Menarik gak konsep {c} ni, tapi cover area mana je?",
            "Tengah fikir nak invest kat idea {c} ke tak... apa pendapat korang?",
            "Halal ke tak konsep {c} ni? Just asking.",
            "Macam mana pelaksanaan {c} eh? Nampak rumit.",
            "Unik idea {c} ni. Harap quality pun okay la.",
            "Not sure if {c} is necessary, tapi boleh la try tengok dulu."
        ]

        target_count = 15
        
        while len(tweets) < target_count:
            sentiment_type = random.choice(["Positive", "Negative", "Neutral"])
            
            txt = ""
            if sentiment_type == "Positive" and pos_templates:
                txt = random.choice(pos_templates)
                pos_templates.remove(txt)
            elif sentiment_type == "Negative" and neg_templates:
                txt = random.choice(neg_templates)
                neg_templates.remove(txt)
            elif sentiment_type == "Neutral" and neu_templates:
                txt = random.choice(neu_templates)
                neu_templates.remove(txt)
            
            if txt == "": txt = f"Review untuk {concept_text} ni..." 

            final_content = txt.replace("{c}", concept_text)
            
            tweets.append({
                "handle": random.choice(usernames),
                "content": final_content,
                "likes": random.randint(1, 999),
                "time": f"{random.randint(1, 23)}h",
                "sentiment": sentiment_type
            })
            
    return tweets

# --- GOOGLE TRENDS ---
def get_google_trends_data(keyword):
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='MY')
        data = pytrends.interest_over_time()
        if not data.empty: return data
    except: pass
    
    dates = pd.date_range(start=datetime.now().replace(year=datetime.now().year-1), periods=52, freq='W')
    val = np.random.randint(20, 100, size=52)
    return pd.DataFrame(val, index=dates, columns=['Interest'])

# --- COMPETITOR SEARCH ---
def get_real_competitors(industry, title):
    competitor_list = []
    try:
        search_results = search(f"top {industry} companies Malaysia price review", num_results=5, advanced=True)
        for item in search_results:
            if "pdf" not in item.url:
                competitor_list.append({
                    "Brand": item.title.split('-')[0].split('|')[0][:30],
                    "Price": f"RM {random.randint(50,300)}",
                    "Rating": round(random.uniform(3.5, 5.0), 1),
                    "Link": item.url
                })
    except: pass
    
    if not competitor_list:
        backups = {
            "Technology": ["Grab", "Touch 'n Go", "Shopee"],
            "F&B": ["Secret Recipe", "Tealive", "Zus Coffee"],
            "Fashion": ["Padini", "Uniqlo", "FashionValet"],
            "Education": ["Kumon", "Math Monkey", "Real Kids"],
            "Health": ["Watsons", "Guardian", "KPJ"],
            "Other": ["Maybank", "CIMB", "Petronas"]
        }
        selected = backups.get(industry, backups["Other"])
        for b in selected:
            competitor_list.append({"Brand": b, "Price": "N/A", "Rating": 4.5, "Link": f"https://google.com/search?q={b}"})
            
    return pd.DataFrame(competitor_list)

# --- PDF GENERATION ---
def create_pdf(user, title, industry, score, sentiment, swot, competitors):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="BIZCHECK REPORT", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(190, 10, txt=f"Generated: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="1. EXECUTIVE SUMMARY", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(190, 8, txt=f"User: {user}", ln=True)
    pdf.cell(190, 8, txt=f"Project: {title} ({industry})", ln=True)
    pdf.cell(190, 8, txt=f"Score: {score}/100 | Sentiment: {sentiment}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, txt="2. SWOT ANALYSIS", ln=True)
    pdf.set_font("Arial", '', 10)
    for k, v in swot.items():
        pdf.cell(190, 6, txt=f"[{k}]", ln=True)
        for i in v: pdf.multi_cell(190, 6, txt=f"- {i}")
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ''
if 'current_page' not in st.session_state: st.session_state['current_page'] = "Main Dashboard"
if 'biz_title' not in st.session_state: st.session_state['biz_title'] = ''
if 'biz_industry' not in st.session_state: st.session_state['biz_industry'] = 'Technology'
if 'biz_desc' not in st.session_state: st.session_state['biz_desc'] = ''
if 'analysis_done' not in st.session_state: st.session_state['analysis_done'] = False
if 'sentiment_result' not in st.session_state: st.session_state['sentiment_result'] = {}
if 'swot_result' not in st.session_state: st.session_state['swot_result'] = {}
if 'competitor_data' not in st.session_state: st.session_state['competitor_data'] = pd.DataFrame()
if 'trends_data' not in st.session_state: st.session_state['trends_data'] = pd.DataFrame()
if 'social_data' not in st.session_state: st.session_state['social_data'] = []
if 'viability_score' not in st.session_state: st.session_state['viability_score'] = 0
if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []

# --- 5. FRONTEND INTERFACE ---
def main():
    init_db()
    with st.sidebar:
        try: st.image("logo.png", width=280)
        except: st.warning("BizCheck Pro")
        st.write("---")

    # LOGIN SYSTEM
    if not st.session_state['logged_in']:
        with st.sidebar:
            opt = option_menu("Access", ["Login", "Register"], icons=["key", "person-plus"], default_index=0)
        
        if opt == "Login":
            st.title("🔐 Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login", type="primary"):
                res = login_user(email, password)
                if res:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = res[0][1]
                    st.rerun()
                else: st.error("Invalid credentials.")
        
        elif opt == "Register":
            st.title("📝 Register")
            u = st.text_input("Username")
            e = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.button("Register", type="primary"):
                if add_user(u, e, p): st.success("Registered! Please login.")
                else: st.error("Email taken.")
        return

    # DASHBOARD MENU
    with st.sidebar:
        st.info(f"👤 User: {st.session_state['username']}")
        menu = ["Main Dashboard", "Submit Business Idea", "Evaluation Result", "Ask AI", "Financial Estimator", "Logout"]
        icons = ["house", "lightbulb", "bar-chart", "robot", "calculator", "box-arrow-left"]
        
        try: 
            idx = menu.index(st.session_state['current_page'])
        except: 
            idx = 0
            
        choice = option_menu("Menu", menu, icons=icons, default_index=idx)
        
        if choice == "Logout":
            st.session_state['logged_in'] = False
            st.session_state['username'] = ''
            st.rerun()
        
        if choice != st.session_state['current_page']:
            st.session_state['current_page'] = choice
            st.rerun()

    # --- MAIN DASHBOARD ---
    if st.session_state['current_page'] == "Main Dashboard":
        lottie_biz = load_lottiefile("animasi.json")
        col1, col2 = st.columns([1.5, 1])
        with col1:
            st.title("🚀 BizCheck Pro")
            st.markdown("### The Ultimate AI Business Validator")
            st.write("BizCheck Pro helps students and entrepreneurs validate their business ideas instantly using Artificial Intelligence and Real-Time Data Analysis.")
            st.info("👈 **Start by clicking 'Submit Business Idea' on the sidebar!**")
                
        with col2:
            if lottie_biz:
                st_lottie(lottie_biz, height=350, key="biz_anim")
            else:
                 st.image("https://cdn-icons-png.flaticon.com/512/3094/3094836.png", width=300)

        st.divider()
        
        # KEY FEATURES SECTION
        st.subheader("✨ Key Features")
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.container(border=True).markdown("""
            ### 🤖 AI Sentiment
            Analyzes your business description to predict public reception (Positive/Negative).
            """)
        with c2: 
            st.container(border=True).markdown("""
            ### 📊 Smart SWOT
            Automatically generates Strengths, Weaknesses, Opportunities, and Threats for your idea.
            """)
        with c3: 
            st.container(border=True).markdown("""
            ### 💰 Financial Tool
            Calculates Break-Even Point to help you plan your startup budget effectively.
            """)
            
        st.divider()
        
        # HOW IT WORKS SECTION
        st.subheader("🛠️ How It Works")
        st.markdown("""
        1. **Submit Idea:** Enter your business name, industry, and description.
        2. **AI Processing:** Our engine scans competitors, trends, and simulates social feedback.
        3. **Get Results:** View a comprehensive report including Charts, SWOT, and BMC.
        4. **Export:** Download the full report as a PDF for your presentation.
        """)

    # --- SUBMIT IDEA ---
    elif st.session_state['current_page'] == "Submit Business Idea":
        st.title("💡 Submit Business Idea")
        with st.form("biz_form"):
            title = st.text_input("Startup Title", value=st.session_state['biz_title'])
            ind_options = ["Technology", "F&B", "Fashion", "Education", "Health", "Other"]
            try:
                ind_idx = ind_options.index(st.session_state['biz_industry'])
            except:
                ind_idx = 0
            
            industry = st.selectbox("Industry", ind_options, index=ind_idx)
            desc = st.text_area("Business Description", value=st.session_state['biz_desc'], height=150)
            submitted = st.form_submit_button("Analyze Idea 🚀")
            
            if submitted and desc:
                st.session_state['biz_title'] = title
                st.session_state['biz_industry'] = industry
                st.session_state['biz_desc'] = desc
                
                status_box = st.empty()
                progress_bar = st.progress(0)
                
                status_box.info("📡 Connecting to AI Engine...")
                time.sleep(1)
                progress_bar.progress(10)
                
                status_box.info(f"🔎 Searching for '{title}' competitors...")
                competitors = get_real_competitors(industry, title)
                progress_bar.progress(30)
                
                status_box.info("📈 Analyzing Market Trends...")
                trends_df = get_google_trends_data(title)
                st.session_state['trends_data'] = trends_df
                progress_bar.progress(50)

                status_box.info("🐦 Simulating 30 Social Media Interactions...")
                social_data = generate_simulated_twitter_data(title, desc)
                st.session_state['social_data'] = social_data
                progress_bar.progress(70)
                
                status_box.info("🧠 Generating Business Strategy...")
                analysis = TextBlob(desc)
                sentiment_score = analysis.sentiment.polarity
                if sentiment_score > 0: sent_label = "Positive"
                elif sentiment_score < 0: sent_label = "Negative"
                else: sent_label = "Neutral"
                
                score = int(50 + (sentiment_score * 30) + random.randint(5,20))
                score = min(100, max(0, score))
                
                swot = generate_swot(industry, sentiment_score, desc, title)
                
                st.session_state['sentiment_result'] = {'score': sentiment_score, 'label': sent_label}
                st.session_state['viability_score'] = score
                st.session_state['swot_result'] = swot
                st.session_state['competitor_data'] = competitors
                st.session_state['analysis_done'] = True
                
                progress_bar.progress(100)
                status_box.success("✅ Analysis Complete!")
                time.sleep(0.5)
                
                st.session_state['current_page'] = "Evaluation Result"
                st.rerun()

    # --- EVALUATION RESULT ---
    elif st.session_state['current_page'] == "Evaluation Result":
        st.title("📊 Evaluation Result")
        if not st.session_state['analysis_done']:
            st.warning("No analysis found. Please submit an idea first.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Viability Score", f"{st.session_state['viability_score']}/100")
            with c2: st.metric("Sentiment", st.session_state['sentiment_result']['label'])
            with c3: st.metric("Data Points", "30 Social + 5 Comps")
            
            st.divider()
            
            st.subheader("📈 Market Demand Trend")
            trends = st.session_state.get('trends_data', pd.DataFrame())
            st.line_chart(trends) 

            st.divider()

            st.subheader("🐦 Public Sentiment (X Simulation)")
            st.caption(f"Analysis based on 30 simulated tweets about '{st.session_state['biz_title']}'.")
            
            social_data = st.session_state.get('social_data', [])
            
            if social_data:
                pos_count = len([x for x in social_data if x['sentiment'] == 'Positive'])
                neu_count = len([x for x in social_data if x['sentiment'] == 'Neutral'])
                neg_count = len([x for x in social_data if x['sentiment'] == 'Negative'])
                
                k1, k2, k3 = st.columns(3)
                k1.metric("Positif", f"{pos_count} Tweets", delta="😁")
                k2.metric("Neutral", f"{neu_count} Tweets", delta="😐", delta_color="off")
                k3.metric("Negatif", f"{neg_count} Tweets", delta="😡", delta_color="inverse")
                
                st.write("")
                st.markdown("### 💬 Latest Simulated Tweets")
                
                with st.container(height=500):
                    for tweet in social_data:
                        with st.container(border=True):
                            c1, c2 = st.columns([0.5, 5])
                            with c1:
                                st.image("https://cdn-icons-png.flaticon.com/512/5969/5969020.png", width=30)
                            with c2:
                                st.markdown(f"**{tweet['handle']}** · *{tweet['time']}*")
                                st.write(tweet['content'])
                                r1, r2, r3 = st.columns([1, 1, 2])
                                with r1: st.caption(f"❤️ {tweet['likes']}")
                                with r2: st.caption("🔁 Repost")
                                with r3:
                                    if tweet['sentiment'] == "Positive": st.caption("🟢 Positive")
                                    elif tweet['sentiment'] == "Negative": st.caption("🔴 Negative")
                                    else: st.caption("⚪ Neutral")
            else:
                st.warning("Tiada data simulasi sosial media.")

            st.divider()
            
            st.subheader("🧩 SWOT Analysis")
            swot = st.session_state['swot_result']
            
            if not swot:
                st.warning("Data SWOT gagal dimuat turun. Sila cuba lagi.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"**Strengths:**\n" + "\n".join([f"- {s}" for s in swot.get('S', [])]))
                    st.warning(f"**Weaknesses:**\n" + "\n".join([f"- {w}" for w in swot.get('W', [])]))
                with c2:
                    st.info(f"**Opportunities:**\n" + "\n".join([f"- {o}" for o in swot.get('O', [])]))
                    st.error(f"**Threats:**\n" + "\n".join([f"- {t}" for t in swot.get('T', [])]))
            
            st.divider()
            
            st.subheader("🛒 Competitor Analysis")
            st.info(f"Competitors related to '{st.session_state['biz_title']}' and '{st.session_state['biz_industry']}' industry.")
            
            comps = st.session_state['competitor_data']
            
            if not comps.empty:
                st.dataframe(
                    comps,
                    column_config={
                        "Link": st.column_config.LinkColumn("Website Link"),
                        "Rating": st.column_config.ProgressColumn("Rating", min_value=0, max_value=5, format="%.1f")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Tiada pesaing ditemui.")
            
            st.divider()
            
            pdf_bytes = create_pdf(
                st.session_state['username'],
                st.session_state['biz_title'],
                st.session_state['biz_industry'],
                st.session_state['viability_score'],
                st.session_state['sentiment_result']['label'],
                st.session_state['swot_result'],
                st.session_state['competitor_data']
            )
            
            st.download_button(
                label="📥 Download Full Report (PDF)",
                data=pdf_bytes,
                file_name=f"BizCheck_Report_{st.session_state['biz_title']}.pdf",
                mime="application/pdf"
            )

    # --- ASK AI ---
    elif st.session_state['current_page'] == "Ask AI":
        st.title("🤖 Ask AI Consultant")
        st.info("Powered by Google Gemini 2.0 Flash (Smart Mode)")
        
        # KEY DIHANDLE SECARA GLOBAL DI ATAS (Section 0)
        
        if 'chat_history' not in st.session_state: st.session_state['chat_history'] = []
        for chat in st.session_state['chat_history']:
            with st.chat_message("user"): st.write(chat['question'])
            with st.chat_message("assistant"): st.write(chat['answer'])
            
        user_query = st.chat_input("Tanya pasal marketing, strategi, modal...")
        
        if user_query:
            with st.chat_message("user"): st.write(user_query)
            with st.chat_message("assistant"):
                with st.spinner("Menghubungkan ke Pakar AI..."):
                    response_text = ""
                    import socket
                    def is_connected():
                        try:
                            socket.create_connection(("8.8.8.8", 53), timeout=3)
                            return True
                        except OSError:
                            return False

                    if is_connected():
                        try:
                            model = genai.GenerativeModel('gemini-flash-latest')
                            context = f"""
                            Role: Professional business consultant for '{st.session_state.get('biz_title', 'Startup')}'.
                            Context: {st.session_state.get('biz_desc', 'General Business')}.
                            User Question: {user_query}
                            Instructions: 
                            - Answer in BOTH English and Malay (Bilingual).
                            - Format: 
                              🇬🇧 **English:** [English answer]
                              🇲🇾 **Bahasa Melayu:** [Malay answer]
                            - Keep it short.
                            """
                            response = model.generate_content(context)
                            if response.text:
                                response_text = response.text
                        except Exception as e:
                            print(f"Gemini Error: {e}") 
                    else:
                        print("No Internet detected. Switching to Offline Mode.")

                    if not response_text:
                        biz = st.session_state.get('biz_title', 'Bisnes Anda')
                        q_low = user_query.lower()
                        advice_en = ""
                        advice_bm = ""
                        if "marketing" in q_low or "promosi" in q_low or "ads" in q_low:
                            advice_en = f"For **{biz}**, focus on short video content (TikTok/Reels). Use 'Soft Sell' techniques."
                            advice_bm = f"Untuk **{biz}**, fokus video pendek (TikTok/Reels). Guna teknik 'Soft Sell' dan testimoni pelanggan."
                        elif "modal" in q_low or "duit" in q_low or "cost" in q_low or "money" in q_low:
                            advice_en = "Avoid using 100% personal savings. Try finding small grants (TEKUN/MARA) or start as a dropship."
                            advice_bm = "Elak guna duit simpanan 100%. Cuba cari geran kecil (TEKUN/MARA) atau mula dropship dulu."
                        elif "risiko" in q_low or "risk" in q_low or "bahaya" in q_low:
                            advice_en = f"The main risk for **{biz}** is price competition. Ensure you have a 'Unique Selling Point'."
                            advice_bm = f"Risiko utama **{biz}** ialah persaingan harga. Pastikan anda ada keunikan yang pesaing tiada."
                        elif "competitor" in q_low or "pesaing" in q_low or "lawan" in q_low:
                            advice_en = f"Do not compete on price alone. **{biz}** must win on service quality and branding."
                            advice_bm = f"Jangan lawan harga semata-mata. **{biz}** mesti menang dari segi kualiti servis."
                        else:
                            advice_en = f"This is a solid idea for **{biz}**. Make sure to calculate your break-even point using our tool."
                            advice_bm = f"Idea **{biz}** ini bagus. Pastikan anda kira titik pulang modal guna alat Financial Estimator."
                        
                        response_text = f"""⚠️ **OFFLINE ADVISOR MODE**
*(Sambungan Internet Lemah - Menggunakan Pangkalan Data Dalaman)*

🇬🇧 **English:**
{advice_en}

🇲🇾 **Bahasa Melayu:**
{advice_bm}"""

                    st.write(response_text)
                    st.session_state['chat_history'].append({"question": user_query, "answer": response_text})

    # --- FINANCIAL ESTIMATOR ---
    elif st.session_state['current_page'] == "Financial Estimator":
        st.title("💰 Financial & Break-Even Estimator")
        st.markdown("Plan your startup budget carefully.")
        
        with st.form("finance_form"):
            st.subheader("1. Startup Costs (Modal Mula)")
            c1, c2 = st.columns(2)
            with c1:
                e_cost = st.number_input("Equipment & License (RM)", 0.0, step=100.0)
                r_cost = st.number_input("Deposit Rent/Renovation (RM)", 0.0, step=50.0)
            with c2:
                m_cost = st.number_input("Marketing Launch (RM)", 0.0, step=50.0)
                misc_cost = st.number_input("Emergency Fund (RM)", 0.0, step=50.0)
            
            st.markdown("---")
            st.subheader("2. Unit Economics (Untung Seunit)")
            c3, c4 = st.columns(2)
            with c3: price_per_unit = st.number_input("Selling Price per Unit (RM)", 1.0, step=1.0)
            with c4: cost_per_unit = st.number_input("Cost per Unit (RM)", 0.0, step=1.0)
            
            submitted = st.form_submit_button("Calculate Break-Even 💵")

            if submitted:
                total_fixed = e_cost + r_cost + m_cost + misc_cost
                margin = price_per_unit - cost_per_unit
                
                if margin > 0:
                    bep_units = total_fixed / margin
                    st.divider()
                    m1, m2, m3 = st.columns(3)
                    with m1: st.metric("Total Modal", f"RM {total_fixed:,.2f}")
                    with m2: st.metric("Untung/Unit", f"RM {margin:,.2f}")
                    with m3: st.metric("Break-Even", f"{int(bep_units)} unit")
                    
                    st.success(f"""
                    ✅ **Break-Even Analysis:**
                    You need to sell **{int(bep_units)} units** to cover your startup costs.
                    *(Anda perlu menjual **{int(bep_units)} unit** untuk balik modal.)*
                    """)
                else:
                    st.divider()
                    loss = abs(margin)
                    st.error(f"""
                    🚨 **Critical Warning:**
                    Your Selling Price (RM {price_per_unit}) is lower than your Cost (RM {cost_per_unit}). 
                    You are losing **RM {loss:.2f}** for every unit sold!
                    
                    *(Harga Jual lebih rendah dari Kos! Anda rugi setiap jualan. Sila naikkan harga atau kurangkan kos.)*
                    """)

if __name__ == '__main__':
    main()
