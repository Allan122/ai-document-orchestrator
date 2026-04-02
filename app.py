import streamlit as st
import google.generativeai as genai
import pdfplumber
import requests
import json

# --- Config & Secrets ---
st.set_page_config(page_title="AI Document Orchestrator", layout="wide")
st.title("📄 AI-Powered Document Orchestrator")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
N8N_WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]
genai.configure(api_key=GEMINI_API_KEY)

# --- Functions ---
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def process_document_with_gemini(text):
    prompt = f"""
    Analyze the following document text and extract key entities. 
    Return the response STRICTLY as a valid JSON object. Do not include markdown.
    If it's an invoice, extract vendor_name, total_amount, date. 
    If it's a resume or contract, extract name, key_terms, etc.
    
    Document Text:
    {text}
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    try:
        cleaned = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.error(f"Failed to parse AI response: {e}")
        return None

# --- UI ---
uploaded_file = st.file_uploader("Upload a Document (PDF)", type=["pdf"])
user_query = st.text_input("Ask an analytical question about this document:")
recipient_email = st.text_input("Recipient Email ID for alerts:")

if uploaded_file and user_query and recipient_email:
    if st.button("Extract Data & Process Workflow"):
        with st.spinner("Processing Document & Running AI Agents..."):
            
            # 1. Python/Gemini Extraction
            document_text = extract_text_from_pdf(uploaded_file)
            extracted_json = process_document_with_gemini(document_text)
            
            if extracted_json:
                # 2. Send to n8n Webhook
                payload = {
                    "extracted_data": extracted_json,
                    "user_query": user_query,
                    "recipient_email": recipient_email,
                    "document_text": document_text
                }
                
                try:
                    response = requests.post(N8N_WEBHOOK_URL, json=payload)
                    
                    if response.status_code == 200:
                        n8n_result = response.json()
                        
                        st.success("Workflow Completed Successfully!")
                        
                        # 3. Display the Four Required Outputs
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("1. Extracted JSON")
                            st.json(extracted_json)
                            
                            st.subheader("2. Final Analytical Answer")
                            st.info(n8n_result.get("analytical_answer", "No answer returned from n8n."))
                            
                        with col2:
                            st.subheader("3. Generated Email Body")
                            st.write(n8n_result.get("email_body", "No email body returned from n8n."))
                            
                            st.subheader("4. System Status")
                            st.success(n8n_result.get("status", "Completed"))
                            
                    else:
                        st.error(f"Webhook failed with status: {response.status_code}")
                except Exception as e:
                    st.error(f"Error connecting to n8n: {e}")