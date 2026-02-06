import streamlit as st
import math

st.set_page_config(page_title="Spartan Model v5.2", layout="centered")
st.title("⚔️ Spartan Model v5.2")
st.markdown("### Dixon-Coles • Elo • Gap Ratings • Kelly Stakes")

# Sidebar inputs
st.sidebar.header("Match Setup")
home_team = st.sidebar.text_input("Home Team", "Arsenal")
away_team = st.sidebar.text_input("Away Team", "Chelsea")

col1, col2 = st.sidebar.columns(2)
elo_home = col1.number_input("Home Elo", 1400, 2000, 1680)
elo_away = col2.number_input("Away Elo", 1400, 2000, 1620)

col3, col4 = st.sidebar.columns(2)
xg_home = col3.number_input("Home xG", 0.0, 3.0, 1.65)
xg_away = col4.number_input("Away xG", 0.0, 3.0, 1.15)

col5, col6, col7 = st.sidebar.columns(3)
shots_h = col5.number_input("H Shots", 0, 30, 14)
sot_h = col6.number_input("H SoT", 0, 15, 5)
corners_h = col7.number_input("H Corners", 0, 20, 11)

col8, col9, col10 = st.sidebar.columns(3)
shots_a = col8.number_input("A Shots", 0, 30, 12)
sot_a = col9.number_input("A SoT", 0, 15, 4)
corners_a = col10.number_input("A Corners", 0, 20, 8)

odds_1 = st.sidebar.number_input("Odds 1", 1.01, 20.0, 1.86)
odds_x = st.sidebar.number_input("Odds X", 1.01, 20.0, 4.12)
odds_2 = st.sidebar.number_input("Odds 2", 1.01, 20.0, 4.27)

is_cup = st.sidebar.checkbox("Cup Match?", value=True)

# Spartan Model calculations
def dixon_coles_prob(home_xg, away_xg, max_goals=10):
    home_win = 0
    draw = 0
    away_win = 0
    
    for i in range(max_goals):
        for j in range(max_goals):
            # Poisson probability
            p_home = (math.exp(-home_xg) * (home_xg ** i)) / math.factorial(i)
            p_away = (math.exp(-away_xg) * (away_xg ** j)) / math.factorial(j)
            
            if i > j:
                home_win += p_home * p_away
            elif i == j:
                draw += p_home * p_away
            else:
                away_win += p_home * p_away
    
    return home_win, draw, away_win

def calculate_predictions():
    # Elo probability
    elo_diff = elo_home - elo_away
    elo_prob = 1 / (1 + 10 ** (-elo_diff / 400))
    
    # Adjusted xG with home advantage
    home_xg_adj = xg_home * 1.25
    away_xg_adj = xg_away * 0.95
    
    # Dixon-Coles outcomes
    h_win, draw, a_win = dixon_coles_prob(home_xg_adj, away_xg_adj)
    
    # Council of Three voting
    elo_vote = elo_prob > 0.5
    poisson_vote = home_xg_adj > away_xg_adj
    context_vote = not (elo_away > elo_home + 100 and is_cup)
    
    consensus = sum([elo_vote, poisson_vote, context_vote])
    
    # BTTS
    p_home_scores = 1 - math.exp(-home_xg_adj)
    p_away_scores = 1 - math.exp(-away_xg_adj)
    btts_prob = p_home_scores * p_away_scores
    
    # Gap Rating (LSE Method)
    sxg_home = (shots_h * 0.11) + (sot_h * 0.25) + (corners_h * 0.03)
    sxg_away = (shots_a * 0.11) + (sot_a * 0.25) + (corners_a * 0.03)
    gap = (sxg_home + sxg_away - 2.7) / 0.32
    
    if gap > 1.5:
        ou_call = "Over 2.5"
        ou_prob = 62
    elif gap < -1.5:
        ou_call = "Under 2.5"
        ou_prob = 68
    else:
        ou_call = "No Prediction"
        ou_prob = 50
    
    # Double Chance Logic
    if consensus >= 2:
        dc_call = "1X"
        dc_prob = (h_win + draw) * 100
        dc_odds = 1 / ((1/odds_1) + (1/odds_x))
    elif consensus <= 1:
        dc_call = "X2"
        dc_prob = (draw + a_win) * 100
        dc_odds = 1 / ((1/odds_x) + (1/odds_2))
    else:
        dc_call = "12"
        dc_prob = (h_win + a_win) * 100
        dc_odds = 1 / ((1/odds_1) + (1/odds_2))
    
    # Kelly Criterion
    def kelly(p, odds):
        if odds <= 1:
            return 0
        b = odds - 1
        q = 1 - p
        f = (b * p - q) / b
        return max(0, f * 0.3 * 100)  # Fractional Kelly 0.3
    
    kelly_dc = kelly(dc_prob/100, dc_odds)
    kelly_btts = kelly(btts_prob, 1.90)  # Assume 1.90 BTTS odds
    
    confidence = "HIGH" if consensus == 3 else "MEDIUM" if consensus == 2 else "LOW"
    
    return {
        'dc_call': dc_call,
        'dc_prob': dc_prob,
        'kelly_dc': kelly_dc,
        'btts_call': "YES" if btts_prob > 0.52 else "NO",
        'btts_prob': btts_prob * 100,
        'kelly_btts': kelly_btts,
        'ou_call': ou_call,
        'ou_prob': ou_prob,
        'gap': gap,
        'confidence': confidence,
        'consensus': consensus
    }

if st.sidebar.button("Generate Prediction", type="primary"):
    result = calculate_predictions()
    
    # Display results
    st.markdown("---")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    with col_res1:
        st.metric("Confidence", result['confidence'])
        st.metric("Council Votes", f"{result['consensus']}/3")
    
    with col_res2:
        st.markdown(f"### 🛡️ Double Chance")
        st.markdown(f"<h1 style='text-align: center; color: #1f77b4;'>{result['dc_call']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>Probability: {result['dc_prob']:.1f}%</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>Kelly: {result['kelly_dc']:.2f}%</p>", unsafe_allow_html=True)
    
    with col_res3:
        st.markdown(f"### ⚽ BTTS")
        st.markdown(f"<h1 style='text-align: center; color: #ff7f0e;'>{result['btts_call']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>Probability: {result['btts_prob']:.1f}%</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-weight: bold;'>Kelly: {result['kelly_btts']:.2f}%</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    col_ou1, col_ou2 = st.columns(2)
    with col_ou1:
        st.markdown(f"### 📊 Over/Under 2.5")
        st.markdown(f"<h2 style='text-align: center; color: #2ca02c;'>{result['ou_call']}</h2>", unsafe_allow_html=True)
    with col_ou2:
        st.markdown(f"### Gap Rating")
        st.markdown(f"<h2 style='text-align: center;'>{result['gap']:.2f}</h2>", unsafe_allow_html=True)
        st.caption("LSE Method: >1.5 = Over, <-1.5 = Under")
    
    # Warning for low confidence
    if result['confidence'] == "LOW":
        st.error("⚠️ LOW CONFIDENCE: Council split. Consider avoiding or reducing stake.")
    elif result['confidence'] == "MEDIUM":
        st.warning("⚠️ MEDIUM CONFIDENCE: Away favorite or cup volatility detected.")

st.markdown("---")
st.caption("Spartan Model v5.2 • Dixon-Coles ρ=-0.1 • Elo K=40 • Kelly Fractional 0.3")