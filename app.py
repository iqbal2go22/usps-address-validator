import streamlit as st
import pandas as pd
import requests
import io

# USPS API credentials
# USPS API credentials
CONSUMER_KEY = "kMt8AuLvXACeHwys6rb0gqxH2TFMK0tmmyAXaC7SiQAWeQHN"
CONSUMER_SECRET = "ZyViTGQUTjwkAAnLIDwYU9rUlHJQPlXWJH8KQCK7Yvngh9qXVgVMn99ZHziQok3r"

# OpenCage API for geocoding
OPENCAGE_API_KEY = "e52347a41d064e48a19091df61ad7a3a"

# ------------------ USPS Auth ------------------
def get_access_token():
    url = "https://apis.usps.com/oauth2/v3/token"
    headers = {"Content-Type": "application/json"}
    payload = {
        "client_id": CONSUMER_KEY,
        "client_secret": CONSUMER_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error("❌ Failed to get USPS access token.")
        return None

# ------------------ USPS Address Validation ------------------
def validate_address(token, street, city, state, zip_code_input, original_full_address):
    url = "https://apis.usps.com/addresses/v3/address"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "streetAddress": street,
        "city": city,
        "state": state
    }
    if zip_code_input:
        params["ZIPCode"] = zip_code_input

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()["address"]
            standardized = f"{data.get('secondaryAddress', '')} {data['streetAddress']}, {data['city']}, {data['state']} {data['ZIPCode']}".strip()
            needs_update = standardized.upper() != original_full_address.upper()

            return {
                "IsValid": True,
                "StandardizedAddress": standardized,
                "ValidationMessage": "",
                "NeedsUpdate": needs_update
            }

        elif response.status_code == 404:
            return {
                "IsValid": False,
                "StandardizedAddress": "",
                "ValidationMessage": "Address Not Found",
                "NeedsUpdate": False
            }
        else:
            return {
                "IsValid": False,
                "StandardizedAddress": "",
                "ValidationMessage": response.text,
                "NeedsUpdate": False
            }
    except Exception as e:
        return {
            "IsValid": False,
            "StandardizedAddress": "",
            "ValidationMessage": str(e),
            "NeedsUpdate": False
        }

# ------------------ Geocoding ------------------
def get_geocode(address):
    url = f"https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": address,
        "key": OPENCAGE_API_KEY,
        "limit": 1
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                lat = results[0]["geometry"]["lat"]
                lng = results[0]["geometry"]["lng"]
                return lat, lng
        return None, None
    except Exception:
        return None, None

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="SiteOne Address Validator", layout="centered")
st.title("📍 SiteOne Address Validator")
st.markdown("Upload an Excel file with columns: **Adress1**, **Adress2**, **City**, **State**, **Zip5**")
st.markdown("The app validates U.S. addresses using USPS and geocodes them using OpenCage.")

uploaded_file = st.file_uploader("📤 Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ File uploaded successfully!")
    st.write("📄 **Preview:**")
    st.dataframe(df.head())

    if st.button("🚀 Validate and Geocode"):
        with st.spinner("🔐 Getting USPS access token..."):
            token = get_access_token()

        if token
