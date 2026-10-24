import numpy as np
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Outbreak Simulator", layout="wide")

# ------------------------------------------------------------------
# 1. DISEASE PRESETS (approximate values: check against UKHSA/WHO
#    before your pitch and cite your sources)
# ------------------------------------------------------------------
PRESETS = {
    "Measles":      {"r0": 15.0, "days": 8,  "death": 0.10, "disab": 0.10, "hosp": 20.0},
    "Polio":        {"r0": 6.0,  "days": 14, "death": 0.03, "disab": 0.50, "hosp": 1.0},
    "Seasonal flu": {"r0": 1.5,  "days": 4,  "death": 0.05, "disab": 0.01, "hosp": 1.0},
    "Custom":       {"r0": 3.0,  "days": 7,  "death": 0.50, "disab": 0.50, "hosp": 5.0},
}


# ------------------------------------------------------------------
# 2. THE MODEL (SIR with vaccination and contact reduction)
# ------------------------------------------------------------------
def simulate(N, I0, r0, infectious_days, coverage, efficacy, contact_reduction, sim_days):
    gamma = 1 / infectious_days                      # recovery rate per day
    beta = r0 * gamma * (1 - contact_reduction)      # transmission rate per day

    immune_fraction = coverage * efficacy            # share protected by vaccine
    S = (N - I0) * (1 - immune_fraction)             # susceptible
    I = float(I0)                                    # infectious
    R = N - S - I                                    # recovered or immune
    S_start = S

    steps_per_day = 10                               # small steps = more accurate
    dt = 1 / steps_per_day

    S_list, I_list, R_list = [S], [I], [R]
    for _ in range(sim_days):
        for _ in range(steps_per_day):
            new_infections = beta * S * I / N * dt
            new_recoveries = gamma * I * dt
            S -= new_infections
            I += new_infections - new_recoveries
            R += new_recoveries
        S_list.append(S)
        I_list.append(I)
        R_list.append(R)

    ever_infected = I0 + (S_start - S)               # everyone infected during outbreak
    days = np.arange(sim_days + 1)
    return days, np.array(S_list), np.array(I_list), np.array(R_list), ever_infected


# ------------------------------------------------------------------
# 3. SIDEBAR: ALL THE SLIDERS
# ------------------------------------------------------------------
st.title("Outbreak Simulator")
st.write(
    "Explore how vaccination and social measures change the spread of an infectious "
    "disease, and how many people are killed or left permanently disabled."
)

st.sidebar.header("Disease")
choice = st.sidebar.selectbox("Disease preset", list(PRESETS))
p = PRESETS[choice]
k = choice  # changing preset resets sliders to that disease's values

r0 = st.sidebar.slider("R0 (people infected by one case)", 0.5, 20.0, p["r0"], 0.1, key=f"r0_{k}")
infectious_days = st.sidebar.slider("Infectious period (days)", 1, 30, p["days"], key=f"d_{k}")

st.sidebar.header("Severity")
death_pct = st.sidebar.slider("Deaths per 100 infections (%)", 0.0, 10.0, p["death"], 0.01, key=f"de_{k}")
disab_pct = st.sidebar.slider("Permanent disability per 100 infections (%)", 0.0, 10.0, p["disab"], 0.01, key=f"di_{k}")
hosp_pct = st.sidebar.slider("Needing hospital care (%)", 0.0, 50.0, p["hosp"], 0.5, key=f"h_{k}")

st.sidebar.header("Interventions")
coverage = st.sidebar.slider("Vaccination coverage (%)", 0, 100, 70) / 100
efficacy = st.sidebar.slider("Vaccine effectiveness (%)", 0, 100, 95) / 100
contact_reduction = st.sidebar.slider("Reduction in contacts (%)", 0, 90, 0) / 100

st.sidebar.header("Population")
N = st.sidebar.slider("Population size", 10_000, 1_000_000, 100_000, 10_000)
I0 = st.sidebar.slider("Initial cases", 1, 100, 10)
sim_days = st.sidebar.slider("Days to simulate", 60, 365, 180, 10)
beds_per_100k = st.sidebar.slider("Hospital beds available (per 100,000)", 0, 300, 50)

# ------------------------------------------------------------------
# 4. RUN THE MODEL: your scenario vs doing nothing
# ------------------------------------------------------------------
days, S, I, R, infected = simulate(N, I0, r0, infectious_days, coverage, efficacy, contact_reduction, sim_days)
_, _, I_base, _, infected_base = simulate(N, I0, r0, infectious_days, 0, efficacy, 0, sim_days)

deaths, deaths_base = infected * death_pct / 100, infected_base * death_pct / 100
disab, disab_base = infected * disab_pct / 100, infected_base * disab_pct / 100

# Key epidemiology numbers
herd_threshold = 1 - 1 / r0 if r0 > 1 else 0
coverage_needed = herd_threshold / efficacy if efficacy > 0 else float("inf")
Re = r0 * (1 - contact_reduction) * (1 - coverage * efficacy)  # effective R at the start

# ------------------------------------------------------------------
# 5. HEADLINE NUMBERS
# ------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("People infected", f"{infected:,.0f}", f"{infected - infected_base:,.0f} vs no action", delta_color="inverse")
c2.metric("Deaths", f"{deaths:,.0f}", f"{deaths - deaths_base:,.0f} vs no action", delta_color="inverse")
c3.metric("Permanently disabled", f"{disab:,.0f}", f"{disab - disab_base:,.0f} vs no action", delta_color="inverse")
c4.metric("Effective R at start", f"{Re:.2f}")

if Re < 1:
    st.success("Effective R is below 1, so the outbreak should die out.")
else:
    st.warning("Effective R is above 1, so the outbreak can spread.")

if coverage_needed <= 1:
    st.info(
        f"Herd immunity threshold: {herd_threshold:.0%}. With this vaccine you need about "
        f"{coverage_needed:.0%} coverage to stop sustained spread (without other measures)."
    )
else:
    st.info("This vaccine alone cannot reach herd immunity for this disease. Other measures are needed.")

# ------------------------------------------------------------------
# 6. GRAPHS
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Epidemic curve", "Hospital pressure", "Lives and disability", "Vaccination sweep"]
)

with tab1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=S, name="Susceptible"))
    fig.add_trace(go.Scatter(x=days, y=I, name="Infectious (your scenario)"))
    fig.add_trace(go.Scatter(x=days, y=R, name="Recovered or immune"))
    fig.add_trace(go.Scatter(x=days, y=I_base, name="Infectious (no action)", line=dict(dash="dash")))
    fig.update_layout(xaxis_title="Day", yaxis_title="People", hovermode="x unified")
    st.plotly_chart(fig)

with tab2:
    capacity = beds_per_100k * N / 100_000
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=I * hosp_pct / 100, name="Hospital demand (your scenario)"))
    fig.add_trace(go.Scatter(x=days, y=I_base * hosp_pct / 100, name="Hospital demand (no action)", line=dict(dash="dash")))
    fig.add_hline(y=capacity, line_color="red", annotation_text="Bed capacity")
    fig.update_layout(xaxis_title="Day", yaxis_title="People needing hospital care")
    st.plotly_chart(fig)
    peak = (I * hosp_pct / 100).max()
    if peak > capacity:
        st.error(f"Peak demand of about {peak:,.0f} exceeds capacity of {capacity:,.0f}. Hospitals would be overwhelmed.")
    else:
        st.success("Peak hospital demand stays within capacity.")
    st.caption("Simplification: assumes people needing hospital care are in hospital for about as long as they are infectious.")

with tab3:
    fig = go.Figure()
    fig.add_trace(go.Bar(name="No action", x=["Deaths", "Permanent disability"], y=[deaths_base, disab_base]))
    fig.add_trace(go.Bar(name="Your scenario", x=["Deaths", "Permanent disability"], y=[deaths, disab]))
    fig.update_layout(barmode="group", yaxis_title="People")
    st.plotly_chart(fig)
    st.write(
        f"Your scenario prevents about **{deaths_base - deaths:,.0f} deaths** and "
        f"**{disab_base - disab:,.0f} cases of permanent disability**."
    )

with tab4:
    coverages = np.linspace(0, 1, 41)
    totals = []
    for c in coverages:
        _, _, _, _, inf = simulate(N, I0, r0, infectious_days, c, efficacy, contact_reduction, sim_days)
        totals.append(inf * (death_pct + disab_pct) / 100)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=coverages * 100, y=totals, name="Deaths + disabilities"))
    fig.add_vline(x=coverage * 100, line_dash="dot", annotation_text="Your coverage")
    fig.update_layout(xaxis_title="Vaccination coverage (%)", yaxis_title="Deaths + permanent disabilities")
    st.plotly_chart(fig)
    st.caption("Notice how outcomes fall sharply once coverage nears the herd immunity threshold.")

st.divider()
st.caption(
    "Educational model. It assumes a well-mixed population, no births, deaths from other causes "
    "or reinfection, and constant behaviour. Disease figures are approximate. Not for clinical use."
)
