import streamlit as st
import json
import random
import gzip
import folium
from streamlit_folium import folium_static
import pandas as pd
import re

# Helper function to determine text color based on background luminance
def get_text_color(bg_color):
    r = int(bg_color[1:3], 16)
    g = int(bg_color[3:5], 16)
    b = int(bg_color[5:7], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return 'black' if luminance > 0.5 else 'white'

# Data loading with caching and flag generation
@st.cache_data
def load_data():
    with gzip.open('database.json.gz', 'rt', encoding='utf-8') as f:
        data = json.load(f)
    postal_dict = {entry['POSTAL']: entry for entry in data}
    for entry in postal_dict.values():
        entry['IS_FLOOD_PRONE'] = random.random() < 0.15
        entry['IS_FLOOD_HOTSPOT'] = random.random() < 0.10
    return postal_dict

# Risk classification function
def get_risk_class(depth):
    if depth < 0.5:
        return "Low", "#50d890"
    elif depth <= 1.0:
        return "Medium", "#ffc26f"
    else:
        return "High", "#ff595e"

# Create flood table rows
def make_flood_table_rows(baseline, rcp85):
    rows = []
    for scenario, depth in zip(['Baseline', 'RCP8.5'], [baseline, rcp85]):
        risk, color = get_risk_class(depth)
        rows.append({
            "Scenario": scenario,
            "Flood Depth (m)": f"{depth:.2f}",
            "Risk Level":  risk,
            "Color": color
        })
    return rows

# Highlight risk levels in table  
def highlight_risk(row, table_rows):
    color = next(r['Color'] for r in table_rows if r["Scenario"] == row["Scenario"])
    return ["", "", f'color: {color}; font-weight: bold;']

# Placeholder for flood depth data
def get_flood_depth(postal_code, lat, lon):
    return random.uniform(0, 1.5), random.uniform(0, 1.5)

# Main UI function
def main():
    # Apply custom CSS for better styling
    st.markdown("""
    <style>
    .section-container {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #e1e5e9;
    }
    
    .risk-indicator {
        border: 1px solid #e1e5e9;
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 8px;
        text-align: center;
        font-weight: 500;
    }
    
    .yes-text {
        color: #dc3545 !important;
        font-weight: bold !important;
    }
    
    .legend-container {
        display: flex; 
        gap: 1.5em; 
        margin-top: 12px; 
        font-size: 0.9em;
        flex-wrap: wrap;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    
    .legend-color {
        width: 15px;
        height: 15px;
        border-radius: 3px;
        display: inline-block;
    }
    
    /* Dark mode adjustments */
    [data-testid="stAppViewContainer"] {
        background-color: var(--background-color);
    }
    
    @media (prefers-color-scheme: dark) {
        .section-container {
            background: rgba(255, 255, 255, 0.05);
            border-color: #30363d;
        }
        .risk-indicator {
            background-color: #21262d;
            border-color: #30363d;
            color: #f0f6fc;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("🌊 Flood Risk Assessment Tool")
    st.markdown("Enter a 6-digit postal code to assess flood risk for a client's asset in Singapore.")

    # Load data
    postal_dict = load_data()

    # Session state management
    if 'postal_search' not in st.session_state:
        st.session_state['postal_search'] = ''
    if 'last_search' not in st.session_state:
        st.session_state['last_search'] = ''

    # Callback for clear button
    def clear_input():
        st.session_state['postal_search'] = ''
        st.session_state['last_search'] = ''

    # Search bar and buttons
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1], gap="small")
        with col1:
            postal_code = st.text_input(
                label="Postal Code",
                value=st.session_state['postal_search'],
                max_chars=6,
                placeholder="e.g., 018989",
                label_visibility="collapsed"
            )
        with col2:
            search = st.button("🔍 Assess Risk", type="primary")
        with col3:
            clear = st.button("🗑️ Clear", on_click=clear_input)

    # Update session state
    st.session_state['postal_search'] = postal_code

    # Input validation
    if postal_code and not re.match(r'^\d{6}$', postal_code):
        st.error("⚠️ Please enter a valid 6-digit postal code (e.g., 018989)")
        return

    # Trigger search
    trigger_search = search or (postal_code and postal_code != st.session_state.get('last_search') and len(postal_code) == 6)

    if trigger_search and postal_code:
        st.session_state['last_search'] = postal_code
        if postal_code in postal_dict:
            entry = postal_dict[postal_code]
            lat, lon = float(entry['LATITUDE']), float(entry['LONGITUDE'])
            depth_baseline, depth_rcp85 = get_flood_depth(postal_code, lat, lon)
            table_rows = make_flood_table_rows(depth_baseline, depth_rcp85)
            df = pd.DataFrame([{k: v for k, v in row.items() if k != "Color"} for row in table_rows])

            is_flood_prone = entry['IS_FLOOD_PRONE']
            is_flood_hotspot = entry['IS_FLOOD_HOTSPOT']

            # Location Details
            st.subheader("📍 Location Details")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Address:** {entry['ADDRESS']}")
                st.write(f"**Road:** {entry['ROAD_NAME']}")
            with col2:
                st.write(f"**Building:** {entry['BUILDING'] if entry['BUILDING'] != 'NIL' else 'N/A'}")
                st.write(f"**Postal Code:** {postal_code}")

            # Flood Risk Summary  
            st.subheader("Flood Risk Summary")
            st.dataframe(
                df.style.apply(lambda r: highlight_risk(r, table_rows), axis=1),
                height=110,
                hide_index=True,
                use_container_width=True
            )
            # Improved Legend
            st.markdown("""
                <div class="legend-container">
                    <strong>Legend:</strong>
                    <div class="legend-item">
                        <span class="legend-color" style="background:#50d890;"></span>
                        <span>Low (&lt;0.5m)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color" style="background:#ffc26f;"></span>
                        <span>Medium (0.5–1.0m)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color" style="background:#ff595e;"></span>
                        <span>High (≥1.0m)</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Additional Risk Indicators
            st.subheader("Additional Risk Indicators")

            col1, col2 = st.columns(2)
            with col1:
                flood_prone_status = '<span class="yes-text">YES</span>' if is_flood_prone else 'NO'
                st.markdown(f'<div class="risk-indicator">Flood-prone Area<br><strong>{flood_prone_status}</strong></div>', unsafe_allow_html=True)

            with col2:
                flood_hotspot_status = '<span class="yes-text">YES</span>' if is_flood_hotspot else 'NO'
                st.markdown(f'<div class="risk-indicator">Flood Hotspot<br><strong>{flood_hotspot_status}</strong></div>', unsafe_allow_html=True)

            # Map with better styling
            st.subheader("Location Map")
            m = folium.Map(location=[lat, lon], zoom_start=16, tiles="OpenStreetMap")
            
            # Add marker with better popup
            popup_text = f"""
            <b>{entry['ADDRESS']}</b><br>
            Postal Code: {postal_code}<br>
            RCP8.5 Risk: {get_risk_class(depth_rcp85)[0]}
            """
            folium.Marker(
                [lat, lon], 
                popup=folium.Popup(popup_text, max_width=250),
                icon=folium.Icon(color="red", icon="home")
            ).add_to(m)
            
            # Risk circle
            risk_level, risk_color = get_risk_class(depth_rcp85)
            folium.Circle(
                location=[lat, lon],
                radius=80,
                color=risk_color,
                weight=3,
                fill=True,
                fill_color=risk_color,
                fill_opacity=0.3,
                popup=f"Risk Level: {risk_level}"
            ).add_to(m)
            
            folium_static(m, width=700, height=400)
            st.markdown('</div>', unsafe_allow_html=True)

            # Quick Guidance for RMs
            with st.expander("💡 Quick Guidance for Risk Assessment"):
                st.markdown("""
                **Climate Scenarios Explained:**
                - **Baseline:** Current rainfall patterns and tidal conditions
                - **RCP8.5:** Future worst-case scenario with increased rainfall and sea level rise
                
                **Risk Assessment Guidelines:**
                - **🟢 Low Risk (< 0.5m):** Minimal flood impact; standard protective measures sufficient
                - **🟡 Medium Risk (0.5-1.0m):** Monitor conditions; consider flood barriers or asset elevation
                - **🔴 High Risk (≥ 1.0m):** Immediate action required; advise comprehensive mitigation strategies
                
                **Key Risk Factors:**
                - **Flood-prone Areas:** Historically low-lying locations with past flooding incidents
                - **Flood Hotspots:** Areas experiencing localized flash flooding despite drainage improvements
                
                Use both scenarios to evaluate current risk and future resilience for insurance and planning decisions.
                """)
        else:
            st.error("❌ Postal code not found in database. Please verify the code and try again.")
    
    elif not postal_code:
        # Show helpful information when no search is active
        st.info("👆 Enter a 6-digit Singapore postal code above to begin risk assessment")

if __name__ == "__main__":
    main()