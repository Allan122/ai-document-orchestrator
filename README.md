# 📄 AI-Powered Document Orchestrator

## Overview
The AI-Powered Document Orchestrator is a web application designed to automate the extraction of structured data from unstructured documents (like PDFs and invoices). Built with **Python** and **Streamlit**, it leverages the **Google Gemini 2.5 Flash API** to parse document text into a strict JSON schema. 

This project also demonstrates **Business Process Automation (BPA)** by routing the extracted JSON data to an **n8n webhook**, which evaluates the data using conditional logic and triggers automated, formatted HTML email alerts based on specific business rules.

## Features
* **Document Parsing:** Extracts raw text from uploaded PDF files using `pdfplumber`.
* **Dynamic AI Extraction:** Uses LLM Prompt Engineering to force Google Gemini to return strictly formatted JSON data (Vendor Name, Total Amount, Date, etc.).
* **Event-Driven Automation:** Sends the extracted payload via HTTP POST requests to an n8n webhook.
* **Conditional Routing:** Evaluates data in n8n (e.g., "If Total Amount > 100") to trigger downstream actions.
* **Professional Alerting:** Automatically generates and sends HTML-formatted emails with the extracted data.

## Tech Stack
* **Frontend/UI:** Streamlit
* **Backend Logic:** Python
* **AI/LLM:** Google Gemini API (`google-generativeai`)
* **Document Processing:** `pdfplumber`
* **Automation/Orchestration:** n8n (Cloud)

## Security
This application utilizes Streamlit's `st.secrets` management to securely handle the Gemini API key and the n8n Webhook URL. Credentials are never hardcoded into the repository.
