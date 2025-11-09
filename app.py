import os
import json
import time
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from evaluators import evaluate_model_output

# ----------------------------
# Load API keys
# ----------------------------
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

if not openai_key or not groq_key:
    st.error("❌ Missing API keys in .env file!")
    st.stop()

openai_client = OpenAI(api_key=openai_key)

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Azure Policy Generator Comparison", layout="wide")
st.title("🛡 AI-Powered Azure Policy JSON Generator (Comparison)")

user_prompt = st.text_area(
    "Enter your policy requirement:",
    placeholder="e.g., Deny creation of VMs with public IP",
)

# ----------------------------
# Improved JSON extractor
# ----------------------------
def extract_json_strict(text):
    text = text.strip()

    # Remove Markdown fences
    text = text.replace("```json", "").replace("```", "")

    # Find outermost JSON
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return {"error": "Invalid JSON", "raw_output": text[:300]}

    json_str = text[start:end+1]

    try:
        return json.loads(json_str)
    except Exception:
        return {"error": "Malformed JSON", "raw_output": json_str[:300]}

# ----------------------------
# Generation
# ----------------------------
if st.button("🚀 Generate & Compare"):

    if not user_prompt.strip():
        st.warning("Enter a policy description first.")
        st.stop()

    with st.spinner("Running inference…"):

        # ==== GPT-4o-mini ====
        start = time.time()
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content":
                        "You are an Azure Policy generator. "
                        "Return only valid JSON, no markdown, no comments."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
            )
            gpt_raw = response.choices[0].message.content
            gpt_output = extract_json_strict(gpt_raw)
        except Exception as e:
            gpt_raw = ""
            gpt_output = {"error": str(e)}
        gpt_eval = evaluate_model_output("GPT-4o-mini", gpt_raw, time.time()-start)

        # ==== Groq Llama-3.3-70B ====
        start = time.time()
        try:
            groq_response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system",
                         "content": "You strictly output JSON only."},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0
                },
                timeout=60
            )

            if groq_response.status_code == 200:
                groq_raw = groq_response.json()["choices"][0]["message"]["content"]
                groq_output = extract_json_strict(groq_raw)
            else:
                groq_raw = ""
                groq_output = {"error": groq_response.text}
        except Exception as e:
            groq_raw = ""
            groq_output = {"error": str(e)}

        groq_eval = evaluate_model_output("Llama-3.3-70B", groq_raw, time.time()-start)

    # ----------------------------
    # Display
    # ----------------------------
    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🧠 GPT-4o-mini")
        st.json(gpt_output)

    with c2:
        st.subheader("⚡ Llama-3.3-70B")
        st.json(groq_output)

    # ----------------------------
    # Comparison Table
    # ----------------------------
    st.markdown("---")
    st.subheader("📊 Comparison Matrix")

    df = pd.DataFrame([gpt_eval, groq_eval]).set_index("Model").T
    st.dataframe(df, use_container_width=True)
