import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ollama
import sqlite3
import os
import requests
import smtplib
import imaplib
import email
from streamlit_lottie import st_lottie
from email.mime.text import MIMEText
from email.header import decode_header

# ==========================================
# 1. DATABASE & MIGRATION
# ==========================================
def init_db():
    conn = sqlite3.connect('agentic_ai.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
    
    # Base table for stats
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats 
                 (username TEXT PRIMARY KEY, sent_count INTEGER DEFAULT 0, reply_count INTEGER DEFAULT 0,
                  positive_replies INTEGER DEFAULT 0, negative_replies INTEGER DEFAULT 0, growth_value FLOAT DEFAULT 0.0)''')
    
    # Ensure migration for all columns
    c.execute("PRAGMA table_info(user_stats)")
    columns = [column[1] for column in c.fetchall()]
    required_cols = {
        "positive_replies": "INTEGER DEFAULT 0",
        "negative_replies": "INTEGER DEFAULT 0",
        "growth_value": "FLOAT DEFAULT 0.0"
    }
    for col, definition in required_cols.items():
        if col not in columns:
            c.execute(f"ALTER TABLE user_stats ADD COLUMN {col} {definition}")
            
    c.execute('CREATE TABLE IF NOT EXISTS credentials (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, gmail TEXT, app_pass TEXT)')
    conn.commit()
    conn.close()

def get_stats(username):
    conn = sqlite3.connect('agentic_ai.db')
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM user_stats WHERE username=?", (username,)).fetchone()
    conn.close()
    if row: return dict(row)
    return {"sent_count": 0, "reply_count": 0, "positive_replies": 0, "negative_replies": 0, "growth_value": 0.0}

def update_stats(username, sent_add=0, reply_add=0):
    conn = sqlite3.connect('agentic_ai.db')
    conn.execute('''UPDATE user_stats SET sent_count = sent_count + ?, reply_count = reply_count + ? 
                    WHERE username = ?''', (sent_add, reply_add, username))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. UI STYLING
# ==========================================
st.set_page_config(page_title="Agentic AI Pro", layout="wide", page_icon="🤖")

st.markdown("""
<style>
    .stApp { background: #F8FAFC; }
    
    /* Sidebar Fix */
    [data-testid="stSidebar"] { background-color: #0F172A !important; }
    [data-testid="stSidebar"] .stButton button {
        background-color: white !important; color: #0F172A !important;
        font-weight: 700 !important; border-radius: 8px; border: none; margin-bottom: 8px;
    }
    
    /* Campaign & Vantage Cards */
    .vantage-card {
        background: white; padding: 30px; border-radius: 16px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .section-title { font-size: 22px; font-weight: 700; color: #0F172A; margin-bottom: 15px; }
    
    /* Process Node styling for Dashboard */
    .process-node {
        border-left: 4px solid #A855F7; padding-left: 20px; margin-bottom: 25px;
    }

    /* Login Box */
    .login-box { background:#0F172A; padding:80px; border-radius:30px; color:white; min-height: 85vh; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIN & CREATE ACCOUNT
# ==========================================
if "authenticated" not in st.session_state: 
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    l, r = st.columns([1.2, 1])
    with l:
        st.markdown(f"""
        <div class="login-box">
            <h2 style='color:#A855F7;'>🤖 Agentic AI</h2>
            <h1 style='font-size:3.5rem; font-weight:800; line-height:1.2;'>
                Next-Gen <br><span style='color:#A855F7'>Autonomous</span> Outreach.
            </h1>
            <p style='color:#94A3B8; font-size:1.2rem; margin-top:20px;'>
                Deploy AI agents to manage your entire GTM motion. 
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with r:
        st.markdown("<div style='padding:80px 20px;'>", unsafe_allow_html=True)
        tab = st.radio("Access Control", ["Sign In", "Create Account"], horizontal=True)
        u = st.text_input("Username / Email")
        p = st.text_input("Password", type="password")
        
        if tab == "Sign In":
            if st.button("Sign In →", type="primary", use_container_width=True):
                conn = sqlite3.connect('agentic_ai.db')
                res = conn.execute("SELECT password FROM users WHERE username=?", (u,)).fetchone()
                if res and res[0] == p:
                    st.session_state.authenticated = True
                    st.session_state.user = u
                    st.rerun()
                else: st.error("Invalid credentials.")
        else:
            if st.button("Register Agent →", type="primary", use_container_width=True):
                conn = sqlite3.connect('agentic_ai.db')
                try:
                    conn.execute("INSERT INTO users VALUES (?,?)", (u, p))
                    conn.execute("INSERT INTO user_stats (username) VALUES (?)", (u,))
                    conn.commit()
                    st.success("Account created! Please Sign In.")
                except: st.error("User already exists.")
    st.stop()

# ==========================================
# 4. NAVIGATION
# ==========================================
current_user = st.session_state.user
with st.sidebar:
    st.markdown("<h2 style='color:white;'>🤖 Agentic AI</h2>", unsafe_allow_html=True)
    st.write("---")
    menu = ["📊 Dashboard", "🚀 Campaign", "📈 Analytics", "👥 Leads", "📥 Sync Inbox", "⚙️ Settings"]
    for item in menu:
        if st.button(item, use_container_width=True): 
            st.session_state.page = item.split(" ")[1]
    st.write("---")
    if st.button("Logout", use_container_width=True): 
        st.session_state.authenticated = False
        st.rerun()

page = st.session_state.get("page", "Dashboard")

# ==========================================
# 5. PAGES
# ==========================================

# --- DASHBOARD ---
if page == "Dashboard":
    st.title("🚀 Agentic AI Command Center")
    stats = get_stats(current_user)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="vantage-card"><small>TOTAL SENT</small><h3>{stats["sent_count"]}</h3></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="vantage-card"><small>TOTAL REPLIES</small><h3>{stats["reply_count"]}</h3></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="vantage-card"><small>CREDITS USED</small><h3>84%</h3></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="vantage-card"><small>SYSTEM UPTIME</small><h3>99.9%</h3></div>', unsafe_allow_html=True)

    col_info, col_flow = st.columns([1, 1.2])
    
    with col_info:
        st.markdown("""
        <div class="vantage-card">
            <h3 class="section-title">What is Agentic AI?</h3>
            <p style="color: #64748B; line-height: 1.6;">
                Agentic AI is an autonomous Go-to-Market (GTM) platform designed to handle the heavy lifting of sales outreach. 
                Our specialized agents scan lead databases, craft hyper-personalized emails, and manage follow-ups 
                using advanced intent detection.
            </p>
            <hr>
            <h4 style="color:#0F172A;">Core Advantages</h4>
            <ul style="color: #64748B;">
                <li><b>Local Intelligence:</b> Powered by Llama 3 for data privacy and zero-latency drafting.</li>
                <li><b>Smart Sync:</b> Real-time inbox monitoring to capture hot inquiries instantly.</li>
                <li><b>Scale without Limits:</b> Automate thousands of touchpoints with human-like precision.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_flow:
        st.markdown('<div class="vantage-card">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-title">Agentic Workflow Process</h3>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="process-node">
            <b style="color:#A855F7;">1. DATA INGESTION & SOURCE</b><br>
            <small>The system pulls prospects from your <code>icp_dataset.csv</code>, segmenting leads by domain and location.</small>
        </div>
        <div class="process-node">
            <b style="color:#A855F7;">2. AI BRAINSTORM & DRAFT</b><br>
            <small>The AI Brain analyzes your campaign goals and creates context-aware outreach messages tailored to each lead.</small>
        </div>
        <div class="process-node">
            <b style="color:#A855F7;">3. AUTONOMOUS DISPATCH</b><br>
            <small>Emails are sent via connected SMTP accounts, rotating profiles to ensure maximum deliverability.</small>
        </div>
        <div class="process-node">
            <b style="color:#A855F7;">4. FEEDBACK LOOP & ANALYTICS</b><br>
            <small>Replies are synced via IMAP. The system logs engagement metrics and updates your growth trajectory in real-time.</small>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- CAMPAIGN (LAUNCH LOGIC FIXED) ---
elif page == "Campaign":
    st.title("Campaign Launchpad")
    
    conn = sqlite3.connect('agentic_ai.db')
    creds_df = pd.read_sql("SELECT gmail, app_pass FROM credentials WHERE username=?", conn, params=(current_user,))
    conn.close()

    if creds_df.empty:
        st.warning("⚠️ No email accounts linked. Please go to Settings first.")
    else:
        st.markdown('<div class="vantage-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Target Audience</div>', unsafe_allow_html=True)
        sel_acc = st.selectbox("Select Sending Account", creds_df['gmail'])
        sel_pass = creds_df[creds_df['gmail'] == sel_acc]['app_pass'].values[0]
        
        col1, col2 = st.columns(2)
        dom = col1.text_input("Domain", placeholder="e.g. Fintech")
        loc = col2.text_input("Location", placeholder="e.g. London")
        goal = st.text_area("Pitching Goal", placeholder="What do you want to achieve?")
        
        if st.button("Filter & Generate Draft", type="primary"):
            if not os.path.exists("icp_dataset.csv"):
                st.error("icp_dataset.csv not found!")
            else:
                df = pd.read_csv("icp_dataset.csv")
                df.columns = [c.strip().lower() for c in df.columns]
                matched = df[(df['domain'].str.contains(dom, case=False, na=False)) & 
                            (df['location'].str.contains(loc, case=False, na=False))]
                
                if matched.empty:
                    st.warning("No matches found in your CSV.")
                else:
                    st.session_state.matched_leads = matched
                    with st.spinner("AI drafting (CPU mode)..."):
                        try:
                            resp = ollama.chat(model='llama3', 
                                              messages=[{'role':'user', 'content': f'Draft cold email for {dom} in {loc}. Goal: {goal}'}],
                                              options={'num_gpu': 0})
                            st.session_state.draft = resp['message']['content']
                        except: st.error("Ollama connection failed.")
        st.markdown('</div>', unsafe_allow_html=True)

        if "draft" in st.session_state and "matched_leads" in st.session_state:
            st.markdown('<div class="vantage-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">Final Review</div>', unsafe_allow_html=True)
            st.write(f"Targets Identified: **{len(st.session_state.matched_leads)}**")
            final_msg = st.text_area("Edit Draft", st.session_state.draft, height=250)
            
            if st.button("Launch Campaign 🚀", use_container_width=True, type="primary"):
                success_count = 0
                progress_bar = st.progress(0)
                
                for i, row in st.session_state.matched_leads.iterrows():
                    try:
                        msg = MIMEText(final_msg)
                        msg['Subject'] = "Business Proposal"
                        msg['From'] = sel_acc
                        msg['To'] = row['email']

                        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                            server.login(sel_acc, sel_pass)
                            server.sendmail(sel_acc, row['email'], msg.as_string())
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to send to {row['email']}: {e}")
                    
                    idx = list(st.session_state.matched_leads.index).index(i)
                    progress_bar.progress((idx + 1) / len(st.session_state.matched_leads))
                
                update_stats(current_user, sent_add=success_count)
                st.success(f"Successfully launched! {success_count} emails sent.")
            st.markdown('</div>', unsafe_allow_html=True)

# --- ANALYTICS ---
elif page == "Analytics":
    st.title("📊 Performance Intelligence")
    stats = get_stats(current_user)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Volume Sent", f"{stats['sent_count']:,}")
    m2.metric("Interaction Rate", f"{(stats['reply_count']/(stats['sent_count'] if stats['sent_count'] > 0 else 1)*100):.1f}%")
    m3.metric("Growth Velocity", f"{stats['growth_value']}%")
    m4.metric("Positive Intent", f"{stats['positive_replies']}")
    
    st.write("---")
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📈 Scaling Trajectory")
        growth_df = pd.DataFrame({
            'Week': ['W1', 'W2', 'W3', 'W4'],
            'Inquiries': [stats['reply_count']*0.2, stats['reply_count']*0.5, stats['reply_count']*0.8, stats['reply_count']]
        })
        fig_growth = px.area(growth_df, x='Week', y='Inquiries', 
                            line_shape='spline', color_discrete_sequence=['#A855F7'])
        fig_growth.update_layout(plot_bgcolor='white')
        st.plotly_chart(fig_growth, use_container_width=True)
        
    with col_r:
        st.subheader("🌪️ Conversion Funnel")
        funnel_data = dict(
            number=[stats['sent_count'], int(stats['sent_count']*0.6), stats['reply_count'], stats['positive_replies']],
            stage=["Sent", "Opened", "Replied", "Positive"]
        )
        fig_funnel = px.funnel(funnel_data, x='number', y='stage', color_discrete_sequence=['#1E293B'])
        st.plotly_chart(fig_funnel, use_container_width=True)

    st.write("---")
    col_b1, col_b2 = st.columns([1.5, 1])
    with col_b1:
        st.subheader("🗺️ Lead Domain Coverage")
        domain_data = pd.DataFrame({
            "Domain": ["SaaS", "Fintech", "HealthTech", "E-commerce", "AI/ML"],
            "Volume": [35, 25, 15, 15, 10],
            "Parent": ["Tech", "Finance", "Healthcare", "Retail", "Tech"]
        })
        fig_tree = px.treemap(domain_data, path=['Parent', 'Domain'], values='Volume',
                             color='Volume', color_continuous_scale='Purples')
        st.plotly_chart(fig_tree, use_container_width=True)

    with col_b2:
        st.subheader("⏱️ Reply Speed Variance")
        fig_radar = go.Figure(data=go.Scatterpolar(
          r=[80, 95, 70, 85, 90],
          theta=['AI Accuracy','Response Time','Lead Quality','Outreach Volume','Inbox Health'],
          fill='toself',
          line_color='#A855F7'
        ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig_radar, use_container_width=True)

# --- LEADS ---
elif page == "Leads":
    st.title("Lead Inventory")
    if os.path.exists("icp_dataset.csv"):
        df = pd.read_csv("icp_dataset.csv")
        search_query = st.text_input("🔍 Search Leads", placeholder="Filter by name, company, or domain...")
        if search_query:
            df = df[df.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.error("icp_dataset.csv not found.")

# --- SETTINGS ---
elif page == "Settings":
    st.title("⚙️ Workspace Settings")
    st.subheader("Mailbox Integration")
    gm = st.text_input("Gmail Address")
    ap = st.text_input("App Password", type="password")
    if st.button("Connect Mailbox"):
        conn = sqlite3.connect('agentic_ai.db')
        conn.execute("INSERT INTO credentials (username, gmail, app_pass) VALUES (?,?,?)", (current_user, gm, ap))
        conn.commit(); conn.close(); st.success("Connected.")
    
    st.write("---")
    st.subheader("Existing Accounts")
    conn = sqlite3.connect('agentic_ai.db')
    creds = conn.execute("SELECT id, gmail FROM credentials WHERE username=?", (current_user,)).fetchall()
    for row in creds:
        c1, c2 = st.columns([4,1])
        c1.info(row[1])
        if c2.button("Delete", key=f"del_{row[0]}"):
            conn.execute("DELETE FROM credentials WHERE id=?", (row[0],))
            conn.commit(); st.rerun()

# --- SYNC (INBOX REPLY AGENT) ---
# --- SYNC (INBOX REPLY AGENT) ---
elif page == "Sync":
    st.title("📥 Inbox Synchronization")
    st.info("Agent is monitoring inboxes for intent-rich replies.")

    conn = sqlite3.connect('agentic_ai.db')
    user_creds = pd.read_sql(
        "SELECT gmail, app_pass FROM credentials WHERE username=?",
        conn,
        params=(current_user,)
    )
    conn.close()

    if user_creds.empty:
        st.warning("⚠️ No email accounts found. Please link an account in Settings first.")
    else:
        if st.button("🔄 Sync Now", type="primary"):
            with st.spinner("Agent is scanning inboxes and replying..."):

                total_replies = 0

                for _, row in user_creds.iterrows():
                    gmail_user = row["gmail"]
                    app_pass = row["app_pass"]

                    try:
                        # Connect to Gmail IMAP
                        mail = imaplib.IMAP4_SSL("imap.gmail.com")
                        mail.login(gmail_user, app_pass)
                        mail.select("inbox")

                        # Search unread mails
                        status, messages = mail.search(None, 'UNSEEN')

                        if status != "OK":
                            continue

                        mail_ids = messages[0].split()

                        for mail_id in mail_ids:

                            res, msg_data = mail.fetch(mail_id, "(RFC822)")

                            if res != "OK":
                                continue

                            for response_part in msg_data:
                                if not isinstance(response_part, tuple):
                                    continue

                                msg = email.message_from_bytes(response_part[1])

                                # Get sender
                                sender = email.utils.parseaddr(msg.get("From"))[1]
                                if not sender:
                                    continue

                                # Decode subject safely
                                subject = msg.get("Subject", "")
                                decoded_subject = decode_header(subject)
                                subject_parts = []
                                for part, enc in decoded_subject:
                                    if isinstance(part, bytes):
                                        subject_parts.append(part.decode(enc or "utf-8", errors="ignore"))
                                    else:
                                        subject_parts.append(part)
                                subject = "".join(subject_parts)

                                # Extract body safely
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            body_bytes = part.get_payload(decode=True)
                                            if body_bytes:
                                                body = body_bytes.decode(errors="ignore")
                                                break
                                else:
                                    body_bytes = msg.get_payload(decode=True)
                                    if body_bytes:
                                        body = body_bytes.decode(errors="ignore")

                                if not body.strip():
                                    continue

                                # AI generate reply
                                prompt = f"""
                                A lead sent this reply:

                                "{body}"

                                Write a professional, polite business reply.
                                """

                                resp = ollama.chat(
                                    model="llama3",
                                    messages=[{"role": "user", "content": prompt}],
                                    options={"num_gpu": 0}
                                )

                                reply_text = resp["message"]["content"]

                                # Send reply back to SAME sender
                                reply_msg = MIMEText(reply_text)
                                reply_msg["Subject"] = f"Re: {subject}"
                                reply_msg["From"] = gmail_user
                                reply_msg["To"] = sender

                                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                                    smtp.login(gmail_user, app_pass)
                                    smtp.sendmail(gmail_user, sender, reply_msg.as_string())

                                # Mark email as seen
                                mail.store(mail_id, '+FLAGS', '\\Seen')

                                total_replies += 1

                        mail.close()
                        mail.logout()

                    except Exception as e:
                        st.error(f"Sync error for {gmail_user}: {e}")

                if total_replies > 0:
                    update_stats(current_user, reply_add=total_replies)
                    st.success(f"Agent successfully replied to {total_replies} inquiries!")
                else:
                    st.info("No new unread replies found.")
