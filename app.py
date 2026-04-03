import streamlit as st
import requests
import json
import pdfplumber

# --- SETUP & SECRETS ---
st.set_page_config(page_title="Document Analysis & Alert System", layout="wide")

try:
    N8N_WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError as e:
    st.error(f"Missing secret: {e}. Please add it to your Streamlit secrets.")
    st.stop()

# --- UI COMPONENTS ---
st.title("📄 Document Analysis & Alert System")

uploaded_file = st.file_uploader("Upload Document", type=["pdf", "txt"])
user_query = st.text_input("Ask an analytical question about the document:")
recipient_email = st.text_input("Recipient Email ID for alerts (Optional):")

# --- MAIN PROCESSING LOGIC ---
if uploaded_file and user_query:
    if st.button("Send Alert Mail"):
        with st.spinner("Analyzing document and running n8n workflow..."):
            try:
                # 1. EXTRACT TEXT FROM PDF OR TXT
                document_text = ""
                if uploaded_file.name.endswith('.pdf'):
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                document_text += text + "\n"
                elif uploaded_file.name.endswith('.txt'):
                    document_text = uploaded_file.getvalue().decode("utf-8")

                # 2. BULLETPROOF DIRECT API CALL TO GEMINI
                prompt = f"""Analyze the following document text and the user's query.
                User's Query: {user_query}
                Based on the query, dynamically identify and extract the 5-8 most relevant key-value pairs needed to answer the user's specific query.
                Return the result ONLY as a raw, structured JSON object. Do not include markdown formatting like ```json.
                Document Text:\n{document_text}"""
                
                gemini_url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){GEMINI_API_KEY}"
                gemini_payload = {"contents": [{"parts": [{"text": prompt}]}]}
                
                gemini_req = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json=gemini_payload)
                
                if gemini_req.status_code != 200:
                    st.error(f"Gemini API Error: {gemini_req.text}")
                    st.stop()
                    
                extracted_text = gemini_req.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Clean up formatting
                if extracted_text.startswith("```json"):
                    extracted_text = extracted_text[7:-3].strip()
                elif extracted_text.startswith("```"):
                    extracted_text = extracted_text[3:-3].strip()

                try:
                    extracted_json = json.loads(extracted_text)
                except json.JSONDecodeError:
                    extracted_json = {"raw_text": extracted_text}

                # 3. THE COMPLETE PAYLOAD FOR N8N
                payload = {
                    "document_text": document_text,
                    "user_query": user_query,
                    "recipient_email": recipient_email if recipient_email else "",
                    "extracted_data": extracted_json 
                }

                # 4. SEND DATA TO N8N
                n8n_response = requests.post(N8N_WEBHOOK_URL, json=payload)
                
                # 5. DISPLAY RESULTS
                if n8n_response.status_code == 200:
                    try:
                        result = n8n_response.json()
                        st.success("Workflow Completed Successfully!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("1. Extracted JSON Data")
                            st.json(extracted_json)
                            st.subheader("4. Final Status")
                            st.info(result.get("status", "Workflow executed without email alert" if not recipient_email else "Alert Sent Successfully"))
                            
                        with col2:
                            st.subheader("2. Analytical Answer")
                            st.write(result.get("analytical_answer", "No answer provided."))
                            st.subheader("3. Email Draft")
                            st.text_area("Email Body", result.get("email_body", "No email draft generated."), height=200)

                    except json.JSONDecodeError:
                        st.error(f"n8n did not return JSON! Raw error: {n8n_response.text}")
                else:
                    st.error(f"Webhook failed! Status: {n8n_response.status_code}. Message: {n8n_response.text}")

            except Exception as e:
                st.error(f"An error occurred while processing: {e}")
