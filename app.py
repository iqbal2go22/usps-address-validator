import streamlit as st
import pandas as pd
import requests
import io

# USPS API credentials
CONSUMER_KEY = "kMt8AuLvXACeHwys6rb0gqxH2TFMK0tmmyAXaC7SiQAWeQHN"
CONSUMER_SECRET = "ZyViTGQUTjwkAAnLIDwYU9rUlHJQPlXWJH8KQCK7Yvngh9qXVgVMn99ZHziQok3r"

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
        st.error("Failed to get USPS access token.")
        return None

def validate_address(token, street, city, state, zip_code):
    url = "https://apis.usps.com/addresses/v3/address"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "streetAddress": street,
        "city": city,
        "state": state
    }
    if zip_code:
        params["ZIPCode"] = zip_code

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()["address"]
            return {
                "IsValid": True,
                "StandardizedAddress": f"{data.get('secondaryAddress', '')} {data['streetAddress']}, {data['city']}, {data['state']} {data['ZIPCode']}".strip(),
                "ValidationMessage": ""
            }
        elif response.status_code == 404:
            return {"IsValid": False, "StandardizedAddress": "", "ValidationMessage": "Not Found"}
        else:
            return {"IsValid": False, "StandardizedAddress": "", "ValidationMessage": response.text}
    except Exception as e:
        return {"IsValid": False, "StandardizedAddress": "", "ValidationMessage": str(e)}

# Streamlit UI
st.title("📬 USPS Address Validator")
st.write("Upload an Excel file with columns: `Adress1`, `Adress2`, `City`, `State`, `Zip5`")

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("File Preview:", df.head())

    if st.button("Validate Addresses"):
        with st.spinner("Getting USPS access token..."):
            token = get_access_token()

        if token:
            results = []
            for i, row in df.iterrows():
                st.text(f"Validating address {i+1} of {len(df)}...")
                street = f"{row.get('Adress2', '')} {row.get('Adress1', '')}".strip()
                result = validate_address(
                    token,
                    street,
                    row.get("City", ""),
                    row.get("State", ""),
                    row.get("Zip5", "")
                )
                df.at[i, 'IsValid'] = result["IsValid"]
                df.at[i, 'StandardizedAddress'] = result["StandardizedAddress"]
                df.at[i, 'ValidationMessage'] = result["ValidationMessage"]

            st.success("Validation complete!")
            st.dataframe(df)

            # Prepare download
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button(
                label="Download Results as Excel",
                data=output.getvalue(),
                file_name="validated_addresses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
