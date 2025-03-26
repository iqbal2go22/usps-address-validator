import streamlit as st
import pandas as pd
import requests
import io
import time

# ------------------ Secrets from Streamlit ------------------
CONSUMER_KEY = st.secrets["USPS_CONSUMER_KEY"]
CONSUMER_SECRET = st.secrets["USUS_CONSUMER_SECRET"]
OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]

# ------------------ USPS Token ------------------
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

# ------------------ USPS Validation ------------------
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
            standardized = f"{data.get('secondaryAddress', '')} {data['streetAddress']}, {data['city']}, {data['state']} {data['ZIPCode']}`.strip()
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

# ------------------ UI ------------------
st.set_page_config(page_title="SiteOne Address Validator", layout="centered")
st.title("\ud83d\udccd SiteOne Address Validator")
st.markdown("Upload an Excel file with columns: **Adress1**, **Adress2**, **City**, **State**, **Zip5**")
st.markdown("The app validates U.S. addresses using USPS and geocodes them using OpenCage.")

uploaded_file = st.file_uploader("\ud83d\udcc4 Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("\u2705 File uploaded successfully!")
    st.write("\ud83d\udcc4 **Preview:**")
    st.dataframe(df.head())

    if st.button("\ud83d\ude80 Validate and Geocode"):
        with st.spinner("\ud83d\udd10 Getting USPS access token..."):
            token = get_access_token()

        if token:
            valid_count = 0
            invalid_count = 0
            update_count = 0

            df['IsValid'] = ''
            df['StandardizedAddress'] = ''
            df['ValidationMessage'] = ''
            df['NeedsUpdate'] = ''
            df['Latitude'] = ''
            df['Longitude'] = ''

            progress = st.progress(0)
            status_text = st.empty()
            total = len(df)
            start_time = time.time()

            for i, row in df.iterrows():
                address1 = str(row.get('Adress1', '')).strip()
                address2 = row.get('Adress2', '')
                address2 = str(address2).strip() if pd.notna(address2) else ''
                street = f"{address2} {address1}".strip()
                city = str(row.get("City", "")).strip()
                state = str(row.get("State", "")).strip()
                zip_code = str(row.get("Zip5", "")).strip()
                original_input = f"{address2} {address1}, {city}, {state} {zip_code}".strip()

                result = validate_address(token, street, city, state, zip_code, original_input)

                df.at[i, 'IsValid'] = result["IsValid"]
                df.at[i, 'StandardizedAddress'] = result["StandardizedAddress"]
                df.at[i, 'ValidationMessage'] = result["ValidationMessage"]
                df.at[i, 'NeedsUpdate'] = result["NeedsUpdate"]

                if result["IsValid"]:
                    valid_count += 1
                    if result["NeedsUpdate"]:
                        update_count += 1
                    lat, lng = get_geocode(result["StandardizedAddress"])
                    df.at[i, 'Latitude'] = lat
                    df.at[i, 'Longitude'] = lng
                else:
                    invalid_count += 1

                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1)
                remaining = int(avg_time * (total - i - 1))
                status_text.text(f"Processing {i+1} of {total}... Estimated time left: {remaining} seconds")
                progress.progress((i + 1) / total)

            st.success(f"\ud83c\udfaf Done! \u2714\ufe0f {valid_count} valid | \u274c {invalid_count} invalid | \u26a0\ufe0f {update_count} need update")

            df_display = df.copy()
            df_display['Status'] = df['IsValid'].apply(lambda x: '✔️ Valid' if x else '❌ Invalid')
            df_display['NeedsUpdate'] = df['NeedsUpdate'].apply(lambda x: '⚠️ Yes' if x else '')

            display_columns = [
                'Adress1', 'Adress2', 'City', 'State', 'Zip5',
                'Status', 'StandardizedAddress', 'NeedsUpdate', 'ValidationMessage',
                'Latitude', 'Longitude'
            ]
            existing_cols = [col for col in display_columns if col in df_display.columns]
            df_display = df_display[existing_cols]

            st.markdown("### \ud83d\udccb Validation Results")
            st.dataframe(df_display.style.applymap(
                lambda val: 'color: green' if val == '✔️ Valid' else (
                    'color: red' if val == '❌ Invalid' else (
                        'color: orange' if val == '⚠️ Yes' else None)),
                subset=['Status', 'NeedsUpdate']
            ))

            # Show map
            geo_df = df[['Latitude', 'Longitude']].dropna()
            if not geo_df.empty:
                st.markdown("### \ud83d\uddfa\ufe0f Customer Locations Map")
                st.map(geo_df)

            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button(
                label="\ud83d\udcc5 Download Results as Excel",
                data=output.getvalue(),
                file_name="validated_addresses_with_geocodes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
