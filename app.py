import streamlit as st
import pandas as pd
import requests
import io

# USPS API credentials
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
        st.error("❌ Failed to get USPS access token.")
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
            return {"IsValid": False, "StandardizedAddress": "", "ValidationMessage": "Address Not Found"}
        else:
            return {"IsValid": False, "StandardizedAddress": "", "ValidationMessage": response.text}
    except Exception as e:
        return {"IsValid": False, "StandardizedAddress": "", "ValidationMessage": str(e)}

# ---------- UI Layout ----------
st.set_page_config(page_title="USPS Address Validator", layout="centered")
st.title("📬 USPS Address Validator")
st.markdown("Upload an Excel file with columns: **Adress1**, **Adress2**, **City**, **State**, **Zip5**")
st.markdown("This tool checks each address against the USPS Address API and gives you a downloadable result.")

uploaded_file = st.file_uploader("📤 Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("✅ File uploaded successfully!")
    st.write("📄 **Preview:**")
    st.dataframe(df.head())

    if st.button("🚀 Validate Addresses"):
        with st.spinner("🔐 Getting USPS access token..."):
            token = get_access_token()

        if token:
            valid_count = 0
            invalid_count = 0

            # Add result columns
            df['IsValid'] = ''
            df['StandardizedAddress'] = ''
            df['ValidationMessage'] = ''

            with st.spinner("📦 Validating each address..."):
                for i, row in df.iterrows():
                    address1 = str(row.get('Adress1', '')).strip()
                    address2 = row.get('Adress2', '')
                    address2 = str(address2).strip() if pd.notna(address2) else ''
                    street = f"{address2} {address1}".strip()
                    city = str(row.get("City", "")).strip()
                    state = str(row.get("State", "")).strip()
                    zip_code = str(row.get("Zip5", "")).strip()

                    result = validate_address(token, street, city, state, zip_code)

                    df.at[i, 'IsValid'] = result["IsValid"]
                    df.at[i, 'StandardizedAddress'] = result["StandardizedAddress"]
                    df.at[i, 'ValidationMessage'] = result["ValidationMessage"]

                    if result["IsValid"]:
                        valid_count += 1
                    else:
                        invalid_count += 1

            st.success(f"🎯 Validation complete! ✔️ {valid_count} valid | ❌ {invalid_count} invalid")

            # Add a status column with emoji for display
            df_display = df.copy()
            df_display['Status'] = df['IsValid'].apply(lambda x: '✔️ Valid' if x else '❌ Invalid')

            # Reorder for display
            display_columns = ['Adress1', 'Adress2', 'City', 'State', 'Zip5', 'Status', 'StandardizedAddress', 'ValidationMessage']
            df_display = df_display[display_columns]

            st.markdown("### 🧾 Validation Results")
            st.dataframe(df_display.style.applymap(
                lambda val: 'color: green' if val == '✔️ Valid' else ('color: red' if val == '❌ Invalid' else None),
                subset=['Status']
            ))

            # Excel download
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button(
                label="📥 Download Results as Excel",
                data=output.getvalue(),
                file_name="validated_addresses.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
