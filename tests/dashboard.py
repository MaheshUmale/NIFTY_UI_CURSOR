# import streamlit as st
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# import pandas as pd
# import numpy as np
# from datetime import datetime

# # 1. Page Configuration
# st.set_page_config(layout="wide", page_title="Institutional Index Derivatives Dashboard")
# st.title("🧮 Institutional Index Derivatives Cockpit (Upstox Engine)")

# # --- MOCK DATA ENGINE (Replace this with your Upstox API integration) ---
# @st.cache_data(ttl=1)  # Refresh every second for live simulation
# def fetch_processed_market_data():
#     time_slots = pd.date_range(start="09:15", end="15:30", freq="5min").strftime("%H:%M").tolist()
#     strikes = list(range(23000, 23500, 50))
    
#     # Intraday timeline data
#     df_timeline = pd.DataFrame({
#         "Time": time_slots[:50],
#         "Spot": np.linspace(23100, 23350, 50) + np.random.normal(0, 15, 50),
#         "COI_PCR": np.linspace(0.8, 1.4, 50) + np.random.normal(0, 0.05, 50),
#         "MaxPain": [23200] * 20 + [23250] * 30,
#         "PremiumFlow": np.linspace(-50000, 120000, 50) + np.random.normal(0, 8000, 50)
#     })
    
#     # Strike chain data
#     df_chain = pd.DataFrame({
#         "Strike": strikes,
#         "Call_OI": np.random.randint(20000, 100000, len(strikes)),
#         "Put_OI": np.random.randint(25000, 110000, len(strikes)),
#         "Call_COI": np.random.randint(-10000, 40000, len(strikes)),
#         "Put_COI": np.random.randint(-5000, 50000, len(strikes)),
#         "IV": np.random.uniform(12.5, 16.0, len(strikes)),
#         "GEX": np.random.uniform(-500000, 800000, len(strikes)),
#         "VWAP": np.linspace(150, 10, len(strikes)),
#         "LTP": np.linspace(155, 8, len(strikes))
#     })
#     return df_timeline, df_chain

# df_time, df_strike = fetch_processed_market_data()

# # ==============================================================================
# # MODULE 1: INSTITUTIONAL POSITIONING & SENTIMENT
# # ==============================================================================
# st.header("📊 1. Institutional Positioning & Sentiment")
# col1, col2 = st.columns(2)

# with col1:
#     # Intraday COI PCR Trend
#     fig1 = make_subplots(specs=[[{"secondary_y": True}]])
#     fig1.add_trace(go.Scatter(x=df_time["Time"], y=df_time["Spot"], name="Spot Price", line=dict(color="white", width=2)), secondary_y=False)
#     fig1.add_trace(go.Scatter(x=df_time["Time"], y=df_time["COI_PCR"], name="COI PCR", line=dict(color="cyan", width=2, dash="dot")), secondary_y=True)
#     fig1.update_layout(title_text="Intraday COI PCR vs Spot Trend", template="plotly_dark", height=350)
#     st.plotly_chart(fig1, width=True)

# with col2:
#     # Strike-Wise OI & COI
#     fig2 = go.Figure()
#     # fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Call_OI"], name="Call Total OI", marker_color="crimson", opacity=0.6))
#     # fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Put_OI"], name="Put Total OI", marker_color="emerald", opacity=0.6))
#     # fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Call_COI"], name="Call Intraday COI", marker_color="darkred"))
#     # fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Put_COI"], name="Put Intraday COI", marker_color="darkgreen"))
#        # Change "crimson" to "#DC143C" and "emerald" to "#10B981"
#     fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Call_OI"], name="Call Total OI", marker_color="#DC143C", opacity=0.6))
#     fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Put_OI"], name="Put Total OI", marker_color="#10B981", opacity=0.6))
#     fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Call_COI"], name="Call Intraday COI", marker_color="darkred"))
#     fig2.add_trace(go.Bar(x=df_strike["Strike"], y=df_strike["Put_COI"], name="Put Intraday COI", marker_color="darkgreen"))

   
   
   
#     fig2.update_layout(barmode="group", title_text="Strike-Wise Total OI vs Intraday COI Change", template="plotly_dark", height=350)
#     st.plotly_chart(fig2, width=True)


# # ==============================================================================
# # MODULE 2: INTRADAY FLOW & BUILDUP QUADRANT
# # ==============================================================================
# st.header("⚡ 2. Intraday Flow & Buildup Quadrant")
# col3, col4 = st.columns([1, 2])

# with col3:
#     # Max Pain Convergence
#     fig3 = go.Figure()
#     fig3.add_trace(go.Scatter(x=df_time["Time"], y=df_time["Spot"], name="Spot Price", line=dict(color="yellow")))
#     fig3.add_trace(go.Scatter(x=df_time["Time"], y=df_time["MaxPain"], name="Max Pain Level", line=dict(color="magenta", shape="hv")))
#     fig3.update_layout(title_text="Max Pain Gravitational Tracking", template="plotly_dark", height=350)
#     st.plotly_chart(fig3, width=True)

# with col4:
#     # Net Gamma Exposure (GEX) Profile
#     fig4 = go.Figure()
#     colors = ["#10B981" if x > 0 else "#DC143C" for x in df_strike["GEX"]]
#     fig4.add_trace(go.Bar(y=df_strike["Strike"], x=df_strike["GEX"], orientation="h", marker_color=colors, name="Net GEX"))
#     fig4.add_vline(x=0, line_dash="dash", line_color="white")
#     fig4.update_layout(title_text="Net Gamma Exposure (GEX) Flip Zones", template="plotly_dark", height=350)
#     st.plotly_chart(fig4, width=True)


# # ==============================================================================
# # MODULE 3: VOLATILITY & PRICING STRUCTURE
# # ==============================================================================
# st.header("📉 3. Volatility & Pricing Structure")
# col5, col6 = st.columns(2)

# with col5:
#     # IV Skew Smile Curve
#     fig5 = go.Figure()
#     fig5.add_trace(go.Scatter(x=df_strike["Strike"], y=df_strike["IV"], mode="lines+markers", name="Live IV Smile", line=dict(color="orange")))
#     fig5.update_layout(title_text="Implied Volatility (IV) Skew Curve", template="plotly_dark", height=350)
#     st.plotly_chart(fig5, width=True)

# with col6:
#     # VWAP vs Option Premium Scatter
#     # fig6 = go.Figure()
#     # Fixed VWAP vs Option Premium Scatter Anchor
#     fig6 = go.Figure()
#     fig6.add_trace(go.Scatter(x=df_strike["VWAP"], y=df_strike["LTP"], mode="markers", marker=dict(size=12, color=df_strike["Strike"], colorscale="Viridis", showscale=True), text=df_strike["Strike"], name="Strikes"))
#     # Filled parameters with real array anchors
#     fig6.add_trace(go.Scatter(x=df_strike["VWAP"], y=df_strike["VWAP"], name="Fair Value Anchor", line=dict(color="gray", dash="dash")))

#     # fig6.add_trace(go.Scatter(x=df_strike["VWAP"], y=df_strike["LTP"], mode="markers", marker=dict(size=12, color=df_strike["Strike"], colorscale="Viridis", showscale=True), text=df_strike["Strike"], name="Strikes"))
#     # fig6.add_trace(go.Scatter(x=[0, 160], y=[0, 160], name="Fair Value Anchor", line=dict(color="gray", dash="dash")))
#     fig6.update_layout(title_text="Option Premium vs Institutional VWAP Divergence", template="plotly_dark", height=350, xaxis_title="VWAP", yaxis_title="LTP")
#     st.plotly_chart(fig6, width=True)


# # ==============================================================================
# # MODULE 4: PREMIUM DIVERGENCE & EXECUTION
# # ==============================================================================
# st.header("🎯 4. Premium Divergence & Execution Matrix")

# fig7 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08)
# fig7.add_trace(go.Scatter(x=df_time["Time"], y=df_time["Spot"], name="Spot Index", line=dict(color="white")), row=1, col=1)
# fig7.add_trace(go.Scatter(x=df_time["Time"], y=df_time["PremiumFlow"], name="Net Premium Flow", line=dict(color="lightgreen"), fill='tozeroy'), row=2, col=1)

# # Highlights divergence (Mock validation logic)
# fig7.add_annotation(x=df_time["Time"].iloc[35], y=df_time["Spot"].iloc[35], text="⚠️ Bearish Divergence Spotted", showarrow=True, arrowhead=1, bgcolor="red", row=1, col=1)

# fig7.update_layout(title_text="Live Premium vs Spot Structural Divergence Tracker", template="plotly_dark", height=500)
# st.plotly_chart(fig7, width=True)

###############################3=========

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import threading
import time
from queue import Queue

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Institutional Derivatives Cockpit", page_icon="🧮")
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)

# 2. Thread-Safe Global State Engines
if "ws_queue" not in st.session_state:
    st.session_state.ws_queue = Queue()
    st.session_state.core_data = {
        "spot_history": [23200.0] * 50,
        "ce_history": [150.0] * 50,
        "pe_history": [130.0] * 50,
        "pcr_history": [1.05] * 50,
        "premium_flow": [0.0] * 50,
        "time_slots": pd.date_range(start="09:15", periods=50, freq="1min").strftime("%H:%M").tolist()
    }

# --- BACKGROUND FEED SIMULATOR ---
# Maps exactly to your Upstox WebSocket & API Calculation workers
def upstox_background_worker(q):
    while True:
        tick = {
            "spot": 23200 + np.random.normal(0, 5),
            "ce_premium": 150 + np.random.normal(0, 3),
            "pe_premium": 130 + np.random.normal(0, 3),
            "pcr": 1.1 + np.random.normal(0, 0.02),
            "volume_oi_ratio_spike": np.random.choice([False, True], p=[0.9, 0.1])
        }
        q.put(tick)
        time.sleep(0.5)

if "worker_initialized" not in st.session_state:
    t = threading.Thread(target=upstox_background_worker, args=(st.session_state.ws_queue,), daemon=True)
    t.start()
    st.session_state.worker_initialized = True

# Consume queue data safely
def sync_telemetry():
    q = st.session_state.ws_queue
    state = st.session_state.core_data
    latest = None
    while not q.empty():
        latest = q.get()
    
    if latest:
        state["spot_history"].append(latest["spot"])
        state["ce_history"].append(latest["ce_premium"])
        state["pe_history"].append(latest["pe_premium"])
        state["pcr_history"].append(latest["pcr"])
        
        # Calculate derived premium flow: CE vs PE delta shifts
        flow = (latest["ce_premium"] * 50000) - (latest["pe_premium"] * 50000)
        state["premium_flow"].append(flow)
        
        # Keep window sliding fixed at 50 ticks
        for key in ["spot_history", "ce_history", "pe_history", "pcr_history", "premium_flow"]:
            state[key] = state[key][-50:]
    return latest

# ==============================================================================
# HEADER FRAGMENT: COMPOSITE MOMENTUM & TRAP STATUS
# ==============================================================================
@st.fragment(run_every=1.0)
def render_header_signals():
    latest = sync_telemetry()
    state = st.session_state.core_data
    
    # Mathematical Feature Derivations
    pcr_slope = state["pcr_history"][-1] - state["pcr_history"][-2]
    vwap_gap = (state["ce_history"][-1] - state["spot_history"][-1]) / state["spot_history"][-1]
    delta_flow = state["premium_flow"][-1] / 5000000  # Normalized against total OI proxy
    
    # 6. Composite Momentum Index Calculation
    w1, w2, w3 = 0.4, 0.3, 0.3
    momentum_index = (w1 * pcr_slope * 10) + (w2 * vwap_gap * 100) + (w3 * delta_flow)
    
    # Trap Index Logic
    pcr_flat = 0.8 <= state["pcr_history"][-1] <= 1.05 and abs(pcr_slope) < 0.005
    vol_oi_spike = latest["volume_oi_ratio_spike"] if latest else False
    is_trapped = pcr_flat or vol_oi_spike
    
    # Determine Signal Output
    if is_trapped:
        signal, color = "NO-GO (TRAP ENGINE ACTIVE - STAY OUT)", "#EF4444"
    elif momentum_index > 0.15:
        signal, color = "GO (BUY CALLS - INSTITUTIONAL MOMENTUM)", "#10B981"
    elif momentum_index < -0.15:
        signal, color = "GO (BUY PUTS - INSTITUTIONAL DISTRIBUTION)", "#DC143C"
    else:
        signal, color = "HOLD (CONFLUENCE SEARCHING)", "#6B7280"
        
    # Render Status
    st.markdown(f"""
    <div style='background-color:#111827; padding:15px; border-radius:10px; border-left: 8px solid {color}; margin-bottom:15px'>
        <span style='color:#9CA3AF; font-size:12px; font-weight:bold; letter-spacing: 1px;'>GLOBAL STRATEGY EXECUTIVE</span>
        <h2 style='margin:0; color:{color}; font-size:24px;'>SYSTEM STATUS: {signal}</h2>
        <p style='margin:5px 0 0 0; color:#E5E7EB; font-size:13px;'>
            <b>Composite Momentum:</b> {momentum_index:.4f} | 
            <b>PCR Slope:</b> {pcr_slope:.4f} | 
            <b>Trap Signature:</b> {'⚠️ DETECTED' if is_trapped else '✅ CLEAR'}
        </p>
    </div>
    """, unsafe_allow_html=True)

render_header_signals()

# Setup Main Columns
col_left, col_right = st.columns([1, 1])

# ==============================================================================
# LEFT COLUMN FRAGMENT: LIVE EXECUTION TERMINAL (Updates ~1s)
# ==============================================================================
@st.fragment(run_every=1.0)
def render_execution_terminal():

    # 1. Update your initialization state to handle OHLC + OI structures
    if "ws_queue" not in st.session_state:
        st.session_state.ws_queue = Queue()
        
        # Generate 50 points of initial OHLC + OI data for Spot, CE, and PE
        base_spot = 23200
        base_ce = 150
        base_pe = 130
    
    st.session_state.core_data = {
        "time_slots": pd.date_range(start="09:15", periods=50, freq="1min").strftime("%H:%M").tolist(),
        
        # Spot Matrix
        "spot_open": [base_spot + np.random.normal(0, 5) for _ in range(50)],
        "spot_high": [base_spot + 15 for _ in range(50)],
        "spot_low": [base_spot - 15 for _ in range(50)],
        "spot_close": [base_spot + np.random.normal(0, 5) for _ in range(50)],
        "spot_oi": [2500000 + i*10000 for i in range(50)],
        
        # CE Premium Matrix
        "ce_open": [base_ce + np.random.normal(0, 3) for _ in range(50)],
        "ce_high": [base_ce + 10 for _ in range(50)],
        "ce_low": [base_ce - 10 for _ in range(50)],
        "ce_close": [base_ce + np.random.normal(0, 3) for _ in range(50)],
        "ce_oi": [1200000 + i*5000 for i in range(50)],
        
        # PE Premium Matrix
        "pe_open": [base_pe + np.random.normal(0, 3) for _ in range(50)],
        "pe_high": [base_pe + 10 for _ in range(50)],
        "pe_low": [base_pe - 10 for _ in range(50)],
        "pe_close": [base_pe + np.random.normal(0, 3) for _ in range(50)],
        "pe_oi": [980000 + i*6000 for i in range(50)],
        
        "premium_flow": [0.0] * 50
    }

# ==============================================================================
# UPDATED LEFT COLUMN FRAGMENT: TRUE CANDLESTICK MATRIX WITH OI OVERLAY
# ==============================================================================
# @st.fragment(run_every=1.0)
# def render_execution_terminal():
#     # 1. Update your initialization state to handle OHLC + OI structures
#     if "ws_queue" not in st.session_state:
#         st.session_state.ws_queue = Queue()
    
#     # Generate 50 points of initial OHLC + OI data for Spot, CE, and PE
#     base_spot = 23200
#     base_ce = 150
#     base_pe = 130
    
#     st.session_state.core_data = {
#         "time_slots": pd.date_range(start="09:15", periods=50, freq="1min").strftime("%H:%M").tolist(),
        
#         # Spot Matrix
#         "spot_open": [base_spot + np.random.normal(0, 5) for _ in range(50)],
#         "spot_high": [base_spot + 15 for _ in range(50)],
#         "spot_low": [base_spot - 15 for _ in range(50)],
#         "spot_close": [base_spot + np.random.normal(0, 5) for _ in range(50)],
#         "spot_oi": [2500000 + i*10000 for i in range(50)],
        
#         # CE Premium Matrix
#         "ce_open": [base_ce + np.random.normal(0, 3) for _ in range(50)],
#         "ce_high": [base_ce + 10 for _ in range(50)],
#         "ce_low": [base_ce - 10 for _ in range(50)],
#         "ce_close": [base_ce + np.random.normal(0, 3) for _ in range(50)],
#         "ce_oi": [1200000 + i*5000 for i in range(50)],
        
#         # PE Premium Matrix
#         "pe_open": [base_pe + np.random.normal(0, 3) for _ in range(50)],
#         "pe_high": [base_pe + 10 for _ in range(50)],
#         "pe_low": [base_pe - 10 for _ in range(50)],
#         "pe_close": [base_pe + np.random.normal(0, 3) for _ in range(50)],
#         "pe_oi": [980000 + i*6000 for i in range(50)],
        
#         "premium_flow": [0.0] * 50
#     }

# ==============================================================================
# UPDATED LEFT COLUMN FRAGMENT: TRUE CANDLESTICK MATRIX WITH OI OVERLAY
# ==============================================================================
# @st.fragment(run_every=1.0)
# def render_execution_terminal():
#     state = st.session_state.core_data
#     x_axis = state["time_slots"]
#     print(state.head())
#     # Calculate 9 EMA based on 'Close' prices
#     def get_ema(data, window=9):
#         return pd.Series(data).ewm(span=window, adjust=False).mean().tolist()
    
#     spot_ema = get_ema(state["spot_close"])
#     ce_ema = get_ema(state["ce_close"])
#     pe_ema = get_ema(state["pe_close"])
    
#     st.markdown("### 📈 Execution Engine & Candlestick Confluence Matrix")
    
#     # 3 Rows, all sharing the same X-axis, each with a secondary Y-axis enabled for OI overlay
#     fig = make_subplots(
#         rows=3, cols=1, 
#         shared_xaxes=True, 
#         vertical_spacing=0.06,
#         specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]],
#         subplot_titles=("SPOT UNDERLYING INDEX", "CE ATM PREMIUM (9 EMA + OI OVERLAY)", "PE ATM PREMIUM (9 EMA + OI OVERLAY)")
#     )
    
#     # ------------------ ROW 1: SPOT INDEX ------------------
#     # Candlestick
#     fig.add_trace(go.Candlestick(
#         x=x_axis, open=state["spot_open"], high=state["spot_high"], low=state["spot_low"], close=state["spot_close"],
#         name="Spot Price", increasing_line_color='#10B981', decreasing_line_color='#EF4444'
#     ), row=1, col=1, secondary_y=False)
#     # 9 EMA Filter
#     fig.add_trace(go.Scatter(x=x_axis, y=spot_ema, name="Spot 9 EMA", line=dict(color="orange", width=1.5)), row=1, col=1, secondary_y=False)
#     # OI Overlay (Area Chart on Secondary Y Axis)
#     fig.add_trace(go.Scatter(x=x_axis, y=state["spot_oi"], name="Spot OI", line=dict(color="rgba(255, 255, 255, 0.15)", width=1), fill='tozeroy'), row=1, col=1, secondary_y=True)

#     # ------------------ ROW 2: CE PREMIUM ------------------
#     # Candlestick
#     fig.add_trace(go.Candlestick(
#         x=x_axis, open=state["ce_open"], high=state["ce_high"], low=state["ce_low"], close=state["ce_close"],
#         name="CE Premium", increasing_line_color='#10B981', decreasing_line_color='#EF4444'
#     ), row=2, col=1, secondary_y=False)
#     # 9 EMA Filter
#     fig.add_trace(go.Scatter(x=x_axis, y=ce_ema, name="CE 9 EMA", line=dict(color="#F59E0B", width=1.5)), row=2, col=1, secondary_y=False)
#     # OI Overlay (Cyan Line on Secondary Y Axis)
#     fig.add_trace(go.Scatter(x=x_axis, y=state["ce_oi"], name="CE OI Trend", line=dict(color="#06B6D4", width=2, dash="dot")), row=2, col=1, secondary_y=True)

#     # ------------------ ROW 3: PE PREMIUM ------------------
#     # Candlestick
#     fig.add_trace(go.Candlestick(
#         x=x_axis, open=state["pe_open"], high=state["pe_high"], low=state["pe_low"], close=state["pe_close"],
#         name="PE Premium", increasing_line_color='#10B981', decreasing_line_color='#EF4444'
#     ), row=3, col=1, secondary_y=False)
#     # 9 EMA Filter
#     fig.add_trace(go.Scatter(x=x_axis, y=pe_ema, name="PE 9 EMA", line=dict(color="#F59E0B", width=1.5)), row=3, col=1, secondary_y=False)
#     # OI Overlay (Magenta Line on Secondary Y Axis)
#     fig.add_trace(go.Scatter(x=x_axis, y=state["pe_oi"], name="PE OI Trend", line=dict(color="#D946EF", width=2, dash="dot")), row=3, col=1, secondary_y=True)

#     # Clean UI styling adjustments
#     fig.update_layout(
#         template="plotly_dark", 
#         height=700,  # Increased height to fit candlestick bars comfortably
#         showlegend=False, 
#         xaxis_rangeslider_visible=False,  # Turn off standard bottom rangeslider to save UI vertical space
#         margin=dict(l=20, r=20, t=30, b=20)
#     )
    
#     # Mute secondary grid lines so the chart stays highly legible
#     fig.update_yaxes(showgrid=False, secondary_y=True)
    
#     st.plotly_chart(fig, use_container_width=True, key="confluence_candlestick_matrix")
    
#     # Premium Divergence Display Block remains underneath
#     st.markdown("### 🌊 Premium Flow Divergence Matrix")
#     fig_div = make_subplots(specs=[[{"secondary_y": True}]])
#     fig_div.add_trace(go.Scatter(x=x_axis, y=state["spot_close"], name="Spot", line=dict(color="#FFFFFF")), secondary_y=False)
#     fig_div.add_trace(go.Scatter(x=x_axis, y=state["premium_flow"], name="Net Premium Flow", fill='tozeroy', line=dict(color="#06B6D4")), secondary_y=True)
#     fig_div.update_layout(template="plotly_dark", height=200, showlegend=False, margin=dict(l=20, r=20, t=10, b=10))
#     st.plotly_chart(fig_div, use_container_width=True, key="divergence_chart")























with col_left:
    render_execution_terminal()

# ==============================================================================
# RIGHT COLUMN FRAGMENT: INSTITUTIONAL CORES (Updates ~5s to preserve performance)
# ==============================================================================
@st.fragment(run_every=5.0)
def render_institutional_core():
    st.markdown("### 📊 Layer C: Absolute OI Walls & Arrival COI Shifts")
    
    # Mock data modeling active option chain profiles
    strikes = list(range(23100, 23450, 50))
    call_oi = [45000, 85000, 120000, 60000, 35000, 20000, 10000] # 23200 is absolute Call Wall
    put_oi =  [15000, 30000, 55000, 95000, 140000, 80000, 40000] # 23300 is absolute Put Wall
    
    # Intraday 1-minute tracking window updates
    call_coi_spike = [2000, -500, 34000, 1200, 500, 200, 0] # Massive 1-min Call COI build at the wall
    put_coi_spike =  [400, 1200, -3000, 15000, 4000, 800, 100]
    
    fig_walls = go.Figure()
    fig_walls.add_trace(go.Bar(x=strikes, y=call_oi, name="Total Call OI", marker_color="#DC143C", opacity=0.4))
    fig_walls.add_trace(go.Bar(x=strikes, y=put_oi, name="Total Put OI", marker_color="#10B981", opacity=0.4))
    fig_walls.add_trace(go.Bar(x=strikes, y=call_coi_spike, name="1-Min Arrival Call COI", marker_color="#8B0000"))
    fig_walls.add_trace(go.Bar(x=strikes, y=put_coi_spike, name="1-Min Arrival Put COI", marker_color="#006400"))
    fig_walls.update_layout(barmode="group", template="plotly_dark", height=320, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig_walls, width=True, key="walls_chart")
    
    st.markdown("### 📉 Volatility-OI Nexus & Gamma Risk Framework")
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        # IV Crush Tracker
        iv_smile = [14.2, 13.8, 13.5, 13.4, 13.6, 14.1, 14.7]
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(x=strikes, y=iv_smile, mode="lines+markers", line=dict(color="#F59E0B", width=2)))
        fig_iv.update_layout(title="Live Implied Volatility (IV) Profile", template="plotly_dark", height=200, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_iv, width=True, key="iv_chart")
        
    with col_v2:
        # GEX Risk Flip profile
        gex_profile = [-300000, -120000, 450000, 890000, 1200000, -40000, -200000]
        colors = ["#10B981" if x > 0 else "#DC143C" for x in gex_profile]
        fig_gex = go.Figure()
        fig_gex.add_trace(go.Bar(x=gex_profile, y=strikes, orientation='h', marker_color=colors))
        fig_gex.add_vline(x=0, line_dash="dash", line_color="white")
        fig_gex.update_layout(title="Net Gamma Exposure (GEX) Zones", template="plotly_dark", height=200, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_gex, width=True, key="gex_chart")

# Layer Validation Summary Grid
st.markdown("### 🎯 Confluence Engine (3-Layer Validation Logs)")
st.info("⚡ Layer A (Market Structure): Higher-High / Higher-Low Confirmed on 5M Frame.")
st.success("⚡ Layer B (Premium Breakout): ATM Call Premium trading cleanly ABOVE its 9 EMA execution boundary.")
st.warning("⚡ Layer C (OI Walls Shift): Price approaching 23200 Call Wall. Evaluating arrival volume spikes.")
with col_right:
    render_institutional_core()
