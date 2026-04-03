import streamlit as st
import requests
import json
import google.generativeai as genai
import pdfplumber

# --- SETUP & SECRETS ---
st.set_page_config(page_title="Document Analysis & Alert System", layout="wide")

# Securely load secrets from Streamlit Cloud (Checklist item 8)
try:
    N8N_WEBHOOK_URL = st.secrets["N8N_WEBHOOK_URL"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except KeyError as e:
    st.error(f"Missing secret: {e}. Please add it to your Streamlit secrets.")
    st.stop()

# --- UI COMPONENTS ---
st.title("📄 Document Analysis & Alert System")

# Accepts both PDF and TXT as per PDF instructions
uploaded_file = st.file_uploader("Upload Document", type=["pdf", "txt"])
user_query = st.text_input("Ask an analytical question about the document:")
# Made email optional so the n8n IF node can actually do its job!
recipient_email = st.text_input("Recipient Email ID for alerts (Optional):")

# --- MAIN PROCESSING LOGIC ---
# Button appears as long as a file and query are provided
if uploaded_file and user_query:
    
    # Exact button label as requested in the PDF checklist
    if st.button("Send Alert Mail"):
        with st.spinner("Analyzing document and running n8n workflow..."):
            try:
                # 1. EXTRACT TEXT FROM PDF OR TXT
                document_text = ""
                if uploaded_file.name.endswith('.pdf'):
                    # Using pdfplumber as explicitly requested in the assignment
                    with pdfplumber.open(uploaded_file) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                document_text += text + "\n"
                elif uploaded_file.name.endswith('.txt'):
                    document_text = uploaded_file.getvalue().decode("utf-8")

                # 2. DYNAMIC STRUCTURED EXTRACTION USING GEMINI (Checklist item 3)
                model = genai.GenerativeModel("gemini-1.5-flash")

                
                # Passing the user_query to guide the dynamic extraction
                prompt = f"""Analyze the following document text and the user's query.
                
                User's Query: {user_query}
                
                Based on the query, dynamically identify and extract the 5-8 most relevant key-value pairs needed to answer the user's specific query.
                Return the result ONLY as a raw, structured JSON object. Do not include markdown formatting like ```json.
                
                Document Text:
                {document_text}"""
                
                response = model.generate_content(prompt)
                extracted_text = response.text.strip()
                
                # Clean up the response in case Gemini adds markdown formatting
                if extracted_text.startswith("```json"):
                    extracted_text = extracted_text[7:-3].strip()
                elif extracted_text.startswith("```"):
                    extracted_text = extracted_text[3:-3].strip()

                # Convert the text into an actual JSON dictionary
                try:
                    extracted_json = json.loads(extracted_text)
                except json.JSONDecodeError:
                    extracted_json = {"raw_text": extracted_text} # Fallback safety

                # 3. THE COMPLETE PAYLOAD (Sending FULL context to n8n)
                payload = {
                    "document_text": document_text,
                    "user_query": user_query,
                    "recipient_email": recipient_email if recipient_email else "",
                    "extracted_data": extracted_json 
                }

                # 4. SEND DATA TO N8N WEBHOOK
                n8n_response = requests.post(N8N_WEBHOOK_URL, json=payload)
                
                # 5. DISPLAY THE 4 REQUIRED OUTPUTS (Checklist item 6)
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
                            st.text_area("Email Body", result.get("email_body", "No email draft generated (Email condition not met)."), height=200)

                    except json.JSONDecodeError:
                        st.error(f"n8n did not return JSON! Here is the raw error from n8n: {n8n_response.text}")
                else:
                    st.error(f"Webhook failed! Status: {n8n_response.status_code}. Message: {n8n_response.text}")

            except Exception as e:
                st.error(f"An error occurred while processing: {e}")