import streamlit as st
import google.generativeai as genai
import pdfplumber
import json
import requests

# 1. Page Configuration
st.set_page_config(page_title="AI Document Orchestrator", layout="centered")
st.title("📄 AI-Powered Document Orchestrator")
st.write("Upload an invoice or document to extract structured data and trigger automated workflows.")

# 2. Secure Configuration Loading
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("Missing API Key. Please configure st.secrets.")

# 3. Helper Functions
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def process_document_with_gemini(text):
    prompt = f"""
    You are an AI data extraction assistant. Analyze the following document text and extract the key information.
    Return the response STRICTLY as a valid JSON object. Do not include any markdown formatting, explanations, or code blocks.
    
    Required JSON Schema:
    {{
        "vendor_name": "string or null",
        "date": "string or null",
        "total_amount": number or null,
        "invoice_number": "string or null",
        "document_type": "string"
    }}
    
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

# 4. User Interface & Logic
uploaded_file = st.file_uploader("Upload a Document (.pdf)", type=["pdf"])

if uploaded_file:
    with st.spinner("Reading document..."):
        document_text = extract_text_from_pdf(uploaded_file)
        
    if st.button("Extract Data & Process"):
        with st.spinner("AI is extracting structured data..."):
            extracted_data = process_document_with_gemini(document_text)
            
            if extracted_data:
                st.success("Extraction Complete!")
                st.json(extracted_data)
                
                st.session_state['extracted_data'] = extracted_data

# 5. n8n Trigger Section
st.markdown("---")
st.subheader("Process Automation")
if st.button("Send to n8n Webhook"):
    if 'extracted_data' in st.session_state:
        webhook_url = st.secrets.get("N8N_WEBHOOK_URL", "")
        if webhook_url:
            try:
                response = requests.post(webhook_url, json=st.session_state['extracted_data'])
                if response.status_code == 200:
                    st.success("Successfully triggered n8n workflow!")
                else:
                    st.error(f"Webhook failed with status: {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: {e}")
        else:
            st.warning("n8n Webhook URL is not configured in secrets yet.")
    else:
        st.warning("Please extract data from a document first.")