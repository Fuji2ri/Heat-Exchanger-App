import math
import random

import streamlit as st
import streamlit.components.v1 as components
from iapws import IAPWS97

st.set_page_config(
    page_title="Heat Exchanger Simulator — LMTD & NTU Calculator",
    page_icon="🔥",
    layout="wide",
)

PAGE_CSS = """
<style>
.stApp { background: radial-gradient(1200px 600px at 50% -10%, #171b2e 0%, #0b0e17 60%); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1250px; padding-top: 2.2rem; }

.app-title {
    text-align: center; font-size: 2.7rem; font-weight: 800; margin: 0; letter-spacing: .5px;
    background: linear-gradient(90deg, #f56858 0%, #fd955e 50%, #f8b64c 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.app-sub { text-align: center; color: #6f7ba3; font-size: 1.05rem; margin: .3rem 0 1.4rem 0; }

.st-key-main_card, .st-key-params_card {
    background: #141828; border: 1px solid #2a2f48; border-radius: 18px; padding: .8rem 1.1rem;
}

/* Show Calculations button (yellow outline, right-aligned) */
.st-key-calc_btn { width: 100% !important; display: flex; justify-content: flex-end; }
[data-testid="stColumn"]:has(.st-key-calc_btn) { align-items: flex-end; }
.st-key-calc_btn > div, .st-key-calc_btn .stButton { width: auto !important; flex: 0 0 auto; }
.st-key-calc_btn button { width: auto !important; min-width: 0; padding: .25rem .9rem; }
.st-key-calc_btn button {
    background: rgba(250, 204, 21, .08); color: #facc15; border: 1px solid #8a7425;
    border-radius: 10px; font-weight: 600;
}
.st-key-calc_btn button:hover { background: rgba(250, 204, 21, .18); border-color: #facc15; color: #ffe27a; }

/* Display Controls dropdown */
[data-testid="stPopover"] button {
    background: #0f1220; color: #e6e9f5; border: 1px solid #2a2f48; border-radius: 12px;
    font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
}

/* red active pill on SI/Imperial and Counter/Parallel */
button[data-testid="stBaseButton-segmented_controlActive"] {
    background: #ef5350 !important; color: #fff !important; border-color: #ef5350 !important;
}

/* parameter rows */
.pcap { color: #6f7ba3; letter-spacing: 1.5px; font-size: .78rem; font-weight: 600; text-transform: uppercase; }
.plabel { color: #8b93b0; font-weight: 700; font-size: .9rem; }
.punit { color: #6f7ba3; font-size: .85rem; white-space: nowrap; }
.st-key-params_card [data-testid="stSliderThumbValue"],
.st-key-params_card [data-testid="stTickBar"] { display: none; }

/* dark inputs */
.st-key-params_card [data-testid="stSelectbox"] div,
.st-key-params_card [data-testid="stSelectbox"] [data-baseweb="select"] > div,
.st-key-params_card [data-testid="stNumberInput"] div,
.st-key-params_card [data-baseweb="select"] > div,
.st-key-params_card [data-baseweb="input"],
.st-key-params_card [data-baseweb="base-input"],
.st-key-params_card [data-testid="stNumberInputContainer"] {
    background-color: #0b0e17 !important; border-color: #2a2f48 !important;
}
.st-key-params_card [data-testid="stSelectbox"] [data-baseweb="select"] > div,
.st-key-params_card [data-testid="stNumberInputContainer"] { border-radius: 10px; border: 1px solid #2a2f48 !important; }
.st-key-params_card [data-testid="stNumberInputContainer"] button { background-color: #0b0e17 !important; }
.st-key-params_card button[data-testid="stBaseButton-segmented_control"] {
    background-color: #0b0e17 !important; border-color: #2a2f48 !important;
}
/* result cards */
.cards { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: .6rem 0 1rem 0; }
.rcard { background: #0b0e17; border: 1px solid #2a2f48; border-radius: 12px; padding: 14px 8px; text-align: center; }
.rcl { font-size: .68rem; letter-spacing: 1px; color: #8b93b0; text-transform: uppercase; }
.rcv { font-family: Consolas, 'Courier New', monospace; font-size: 1.35rem; font-weight: 700; color: #ef5350; margin-top: 6px; }
.rcv small { font-size: .78rem; font-weight: 400; color: #8b93b0; }

/* equations header / footer */
.eqh { font-size: 1.25rem; color: #e6e9f5; margin-top: .4rem; }
.eqsub { color: #6f7ba3; font-size: .82rem; margin-bottom: .5rem; }
.eqfoot { color: #6f7ba3; font-size: .82rem; margin-top: .6rem; }
</style>
"""
st.markdown(PAGE_CSS, unsafe_allow_html=True)

st.markdown('<h1 class="app-title">Heat Exchanger Simulator — LMTD &amp; NTU Calculator</h1>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-sub">Live Temperature Profiles • LMTD &amp; NTU Methods • Counter &amp; Parallel Flow</div>',
    unsafe_allow_html=True,
)

# ---- FLUIDS ----

CP_CONST = {  # kJ/kg·K
    "Water": 4.18,
    "Steam": 2.01,
    "Air": 1.005,
    "Engine Oil": 2.10,
    "Ethylene Glycol": 2.42,
}
FLUIDS = list(CP_CONST.keys())


def get_cp(fluid, temp_c, use_iapws):
    if use_iapws and fluid in ("Water", "Steam"):
        try:
            return IAPWS97(T=temp_c + 273.15, P=3.0).cp
        except Exception:
            return CP_CONST[fluid]
    return CP_CONST[fluid]

# ---- PRESETS, RANGES, UNIT CONVERSION ----

PRESETS = {
    "Water–water shell & tube": ("Water", "Water", 150.0, 25.0, 2.0, 3.0, 500.0, 10.0),
    "Engine oil cooler": ("Engine Oil", "Water", 120.0, 20.0, 1.5, 4.0, 350.0, 12.0),
    "Car radiator (air cooled)": ("Water", "Air", 95.0, 20.0, 1.2, 5.0, 100.0, 15.0),
    "Glycol chiller": ("Water", "Ethylene Glycol", 40.0, -5.0, 2.5, 2.5, 600.0, 8.0),
    "Steam condenser duty": ("Steam", "Water", 100.0, 15.0, 0.5, 10.0, 2000.0, 20.0),
}
DEFAULTS = dict(hot_fluid="Water", cold_fluid="Water", Thi=150.0, Tci=25.0, mh=2.0, mc=3.0, U=500.0, A=10.0)

RANGES = { 
    "Thi": (-20.0, 350.0, 1.0),
    "Tci": (-50.0, 200.0, 1.0),
    "mh": (0.1, 20.0, 0.1),
    "mc": (0.1, 20.0, 0.1),
    "U": (10.0, 3000.0, 10.0),
    "A": (1.0, 100.0, 0.5),
}
IMP_STEP = {"Thi": 1.0, "Tci": 1.0, "mh": 0.1, "mc": 0.1, "U": 1.0, "A": 1.0}
KG_LB, WM2K_BTU, M2_FT2, KW_BTUH = 2.20462262, 1 / 5.678263, 10.7639104, 3412.142

CONV = {  
    "Thi": {"SI": (lambda c: c, lambda c: c), "Imperial": (lambda c: c * 1.8 + 32, lambda f: (f - 32) / 1.8)},
    "Tci": {"SI": (lambda c: c, lambda c: c), "Imperial": (lambda c: c * 1.8 + 32, lambda f: (f - 32) / 1.8)},
    "mh": {"SI": (lambda x: x, lambda x: x), "Imperial": (lambda x: x * KG_LB, lambda x: x / KG_LB)},
    "mc": {"SI": (lambda x: x, lambda x: x), "Imperial": (lambda x: x * KG_LB, lambda x: x / KG_LB)},
    "U": {"SI": (lambda x: x, lambda x: x), "Imperial": (lambda x: x * WM2K_BTU, lambda x: x / WM2K_BTU)},
    "A": {"SI": (lambda x: x, lambda x: x), "Imperial": (lambda x: x * M2_FT2, lambda x: x / M2_FT2)},
}
UNIT_LABEL = {
    "SI": {"Thi": "°C", "Tci": "°C", "mh": "kg/s", "mc": "kg/s", "U": "W/m²·K", "A": "m²"},
    "Imperial": {"Thi": "°F", "Tci": "°F", "mh": "lb/s", "mc": "lb/s", "U": "BTU/h·ft²·°F", "A": "ft²"},
}
NUM_FMT = {"Thi": "%.1f", "Tci": "%.1f", "mh": "%.1f", "mc": "%.1f", "U": "%g", "A": "%g"}

ss = st.session_state
for k, v in DEFAULTS.items():
    ss.setdefault(f"v_{k}", v)
ss.setdefault("hot_fluid", "Water")
ss.setdefault("cold_fluid", "Water")
ss.setdefault("show_calc", True)

def cur_units():
    return ss.get("units") or "SI"

def apply_preset():
    p = PRESETS.get(ss.preset)
    if p:
        ss.hot_fluid, ss.cold_fluid = p[0], p[1]
        for name, val in zip(("Thi", "Tci", "mh", "mc", "U", "A"), p[2:]):
            ss[f"v_{name}"] = val

def disp_range(name, u):
    lo, hi, step = RANGES[name]
    if u == "SI":
        return lo, hi, step
    to_d = CONV[name][u][0]
    return round(to_d(lo), 2), round(to_d(hi), 2), IMP_STEP[name]

def sync_param(name, wkey):
    val = ss.get(wkey)
    if val is None:
        return
    lo, hi, _ = RANGES[name]
    ss[f"v_{name}"] = min(max(CONV[name][cur_units()][1](float(val)), lo), hi)

# ---- PAGE SETUP ----

main_card = st.container(key="main_card")
params_card = st.container(key="params_card")

with main_card:
    left, right = st.columns([3, 1])
    with left:
        with st.popover("Display Controls"):
            animate = st.toggle("Animate flow", True)
            speed = st.slider("Animation speed", 0.25, 3.0, 1.0, 0.25)
            n_tubes = st.slider("Number of tubes", 1, 5, 3)
            n_particles = st.slider("Hot-fluid particles", 0, 30, 9)
            show_legend = st.toggle("Show legend & temperature bar", True)
            show_grid = st.toggle("Show chart grid", True)
            show_pill = st.toggle("Show Q = UA ΔTlm badge", True)
            use_iapws = st.toggle("Use IAPWS-97 Cp for water/steam", False)
    with right:
        btn_label = "🧮 Hide Calculations" if ss.show_calc else "🧮 Show Calculations"
        if st.button(btn_label, key="calc_btn"):
            ss.show_calc = not ss.show_calc
            st.rerun()
    scene_slot = st.empty()

# ---- PARAMETERS CARD ----

with params_card:
    r1 = st.columns([0.6, 1.6, 0.7, 5.2], vertical_alignment="center")
    r1[0].markdown('<div class="pcap">Units</div>', unsafe_allow_html=True)
    with r1[1]:
        st.segmented_control("Units", ["SI", "Imperial"], default="SI", key="units", label_visibility="collapsed")
    r1[2].markdown('<div class="pcap">Preset</div>', unsafe_allow_html=True)
    with r1[3]:
        st.selectbox("Preset", ["Custom..."] + list(PRESETS.keys()), key="preset",
                     on_change=apply_preset, label_visibility="collapsed")
    units = cur_units()

    r2 = st.columns([0.6, 3.0, 5.5], vertical_alignment="center")
    r2[0].markdown('<div class="pcap">Flow</div>', unsafe_allow_html=True)
    with r2[1]:
        st.segmented_control("Flow", ["Counter Flow", "Parallel Flow"], default="Counter Flow",
                             key="flow", label_visibility="collapsed")
    flow_type = ss.get("flow") or "Counter Flow"

    def fluid_label(name):
        if use_iapws and name in ("Water", "Steam"):
            return f"{name} (Cp: IAPWS-97)"
        cp = CP_CONST[name] if units == "SI" else CP_CONST[name] / 4.1868
        return f"{name} (Cp={cp:.2f})"

    r3 = st.columns([0.9, 3, 0.9, 3], vertical_alignment="center")
    r3[0].markdown('<div class="plabel">Hot Fluid</div>', unsafe_allow_html=True)
    with r3[1]:
        hot_fluid_name = st.selectbox("Hot Fluid", FLUIDS, key="hot_fluid", format_func=fluid_label,
                                      label_visibility="collapsed")
    r3[2].markdown('<div class="plabel">Cold Fluid</div>', unsafe_allow_html=True)
    with r3[3]:
        cold_fluid_name = st.selectbox("Cold Fluid", FLUIDS, key="cold_fluid", format_func=fluid_label,
                                       label_visibility="collapsed")

    for name in RANGES:
        lo, hi, _ = disp_range(name, units)
        d = min(max(CONV[name][units][0](ss[f"v_{name}"]), lo), hi)
        ss[f"{name}_sl_{units}"] = float(d)
        ss[f"{name}_nu_{units}"] = float(d)

    def param_row(slot, name, label_html):
        lo, hi, step = disp_range(name, units)
        skey, nkey = f"{name}_sl_{units}", f"{name}_nu_{units}"
        with slot:
            c = st.columns([1.0, 2.2, 1.6, 1.15], vertical_alignment="center")
            c[0].markdown(f'<div class="plabel">{label_html}</div>', unsafe_allow_html=True)
            c[1].slider(name, lo, hi, step=step, key=skey, label_visibility="collapsed",
                        on_change=sync_param, args=(name, skey))
            c[2].number_input(name, lo, hi, step=step, key=nkey, format=NUM_FMT[name],
                              label_visibility="collapsed", on_change=sync_param, args=(name, nkey))
            c[3].markdown(f'<div class="punit">{UNIT_LABEL[units][name]}</div>', unsafe_allow_html=True)

    ul = UNIT_LABEL[units]
    row = st.columns(2, gap="large")
    param_row(row[0], "Thi", "T<sub>h,in</sub>")
    param_row(row[1], "Tci", "T<sub>c,in</sub>")
    row = st.columns(2, gap="large")
    param_row(row[0], "mh", f"ṁ<sub>h</sub> ({ul['mh']})")
    param_row(row[1], "mc", f"ṁ<sub>c</sub> ({ul['mc']})")
    row = st.columns(2, gap="large")
    param_row(row[0], "U", f"U ({ul['U']})")
    param_row(row[1], "A", f"Area ({ul['A']})")

    T_h_in, T_c_in = ss.v_Thi, ss.v_Tci
    m_dot_h, m_dot_c = ss.v_mh, ss.v_mc
    U, Area = ss.v_U, ss.v_A

    cp_h = get_cp(hot_fluid_name, T_h_in, use_iapws)
    cp_c = get_cp(cold_fluid_name, T_c_in, use_iapws)
    C_h, C_c = m_dot_h * cp_h, m_dot_c * cp_c
    C_min, C_max = min(C_h, C_c), max(C_h, C_c)
    C_r = C_min / C_max
    NTU = (U * Area) / (C_min * 1000.0)

    if flow_type == "Counter Flow":
        if abs(C_r - 1.0) < 1e-4:
            epsilon = NTU / (1.0 + NTU)
        else:
            e = math.exp(-NTU * (1.0 - C_r))
            epsilon = (1.0 - e) / (1.0 - C_r * e)
    else:
        epsilon = (1.0 - math.exp(-NTU * (1.0 + C_r))) / (1.0 + C_r)

    Q = epsilon * C_min * (T_h_in - T_c_in)
    T_h_out = T_h_in - Q / C_h
    T_c_out = T_c_in + Q / C_c

    if flow_type == "Counter Flow":
        dT1, dT2 = T_h_in - T_c_out, T_h_out - T_c_in
    else:
        dT1, dT2 = T_h_in - T_c_in, T_h_out - T_c_out

    if dT1 <= 0 or dT2 <= 0:
        LMTD = 0.0
    elif abs(dT1 - dT2) < 1e-4:
        LMTD = dT1
    else:
        LMTD = (dT1 - dT2) / math.log(dT1 / dT2)

    if units == "SI":
        tconv = lambda c: c
        dconv = lambda c: c
        tu, q_txt, q_unit = "°C", f"{Q:.1f}", "kW"
    else:
        tconv = lambda c: c * 1.8 + 32
        dconv = lambda c: c * 1.8
        tu, q_txt, q_unit = "°F", f"{Q * KW_BTUH:,.0f}", "BTU/h"

    # ---- results ----

    st.markdown(
        '<div class="cards">'
        f'<div class="rcard"><div class="rcl">Heat Rate (Q)</div><div class="rcv">{q_txt} <small>{q_unit}</small></div></div>'
        f'<div class="rcard"><div class="rcl">LMTD</div><div class="rcv">{dconv(LMTD):.1f} <small>{tu}</small></div></div>'
        f'<div class="rcard"><div class="rcl">Effectiveness</div><div class="rcv">{epsilon * 100:.1f} <small>%</small></div></div>'
        f'<div class="rcard"><div class="rcl">NTU</div><div class="rcv">{NTU:.2f}</div></div>'
        f'<div class="rcard"><div class="rcl">T<sub>h,out</sub></div><div class="rcv">{tconv(T_h_out):.1f} <small>{tu}</small></div></div>'
        f'<div class="rcard"><div class="rcl">T<sub>c,out</sub></div><div class="rcv">{tconv(T_c_out):.1f} <small>{tu}</small></div></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ---- show caclulations ----

    if ss.show_calc:
        st.markdown(
            '<div class="eqh">▼ <b>Live Equations</b> — the two methods, with your current numbers</div>'
            '<div class="eqsub">All working in SI. Displayed in SI.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("**1 · Capacity rates**")
        st.latex(
            rf"C_h = \dot m_h c_{{p,h}} = {C_h:.3f}\ \mathrm{{kW/K}}, \qquad "
            rf"C_c = \dot m_c c_{{p,c}} = {C_c:.3f}\ \mathrm{{kW/K}}"
        )
        st.latex(rf"C_{{min}} = {C_min:.3f}, \quad C_r = \frac{{C_{{min}}}}{{C_{{max}}}} = {C_r:.3f}")

        st.markdown("**2 · LMTD method**")
        st.latex(rf"\Delta T_1 = {dT1:.1f}^\circ C, \quad \Delta T_2 = {dT2:.1f}^\circ C")
        st.latex(
            rf"\Delta T_{{lm}} = \frac{{\Delta T_1 - \Delta T_2}}{{\ln(\Delta T_1/\Delta T_2)}} = {LMTD:.2f}^\circ C"
        )
        st.latex(
            rf"Q = UA\,\Delta T_{{lm}} = {U:g} \times {Area:g} \times {LMTD:.2f} / 1000 "
            rf"= {U * Area * LMTD / 1000:.1f}\ \mathrm{{kW}}"
        )

        st.markdown("**3 · NTU–effectiveness method**")
        st.latex(rf"NTU = \frac{{UA}}{{C_{{min}}}} = {NTU:.3f}")
        st.latex(
            rf"\varepsilon = {epsilon * 100:.1f}\%, \quad "
            rf"Q = \varepsilon\, C_{{min}}(T_{{h,in}} - T_{{c,in}}) = {Q:.1f}\ \mathrm{{kW}}"
        )
        st.markdown(
            '<div class="eqfoot">The two methods are equivalent — they are two ways of writing the same energy balance.</div>',
            unsafe_allow_html=True,
        )


# ---- Diagrams helpers ----

_STOPS = [(0.0, (66, 165, 245)), (0.5, (156, 106, 214)), (1.0, (239, 83, 80))]

def temp_color(T, lo, hi):
    t = 0.5 if hi - lo < 1e-9 else max(0.0, min(1.0, (T - lo) / (hi - lo)))
    for (t0, c0), (t1, c1) in zip(_STOPS, _STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return "rgb(%d,%d,%d)" % tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return "rgb(239,83,80)"

def fmt(T):
    s = f"{T:.1f}"
    return s[:-2] if s.endswith(".0") else s

def arrow(xa, xb, y, color):
    d = 1 if xb > xa else -1
    return (
        f'<line x1="{xa}" y1="{y}" x2="{xb - 7 * d}" y2="{y}" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>'
        f'<polygon points="{xb},{y} {xb - 9 * d},{y - 5} {xb - 9 * d},{y + 5}" fill="{color}"/>'
    )

def label(x, y, anchor, color, txt):
    return (
        f'<text x="{x}" y="{y + 5}" text-anchor="{anchor}" fill="{color}" '
        f'font-size="15" font-weight="700">{txt}</text>'
    )

def exchanger_svg(flow, Thi, Tho, Tci, Tco, tu, n_tubes, n_particles, speed, animate, show_legend):
    W, H = 1000, 300
    x0, x1, y0, y1 = 190, 810, 36, 250
    counter = flow == "Counter Flow"
    lo, hi = min(Thi, Tho, Tci, Tco), max(Thi, Tho, Tci, Tco)
    col = lambda T: temp_color(T, lo, hi)

    if n_tubes == 1:
        tube_ys = [143]
    else:
        tube_ys = [84 + (202 - 84) * i / (n_tubes - 1) for i in range(n_tubes)]

    tube_left = col(Tco) if counter else col(Tci)
    tube_right = col(Tci) if counter else col(Tco)
    rng = random.Random(11)
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    s.append(
        "<defs>"
        f'<linearGradient id="shellG" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{col(Thi)}"/>'
        f'<stop offset="1" stop-color="{col(Tho)}"/></linearGradient>'
        f'<linearGradient id="tubeG" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{tube_left}"/>'
        f'<stop offset="1" stop-color="{tube_right}"/></linearGradient>'
        '<radialGradient id="hotP" cx="35%" cy="35%" r="70%"><stop offset="0" stop-color="#ffd0da"/>'
        '<stop offset="1" stop-color="#e0476e"/></radialGradient>'
        '<linearGradient id="barG" x1="0" x2="1"><stop offset="0" stop-color="rgb(66,165,245)"/>'
        '<stop offset=".5" stop-color="rgb(156,106,214)"/><stop offset="1" stop-color="rgb(239,83,80)"/></linearGradient>'
        "</defs>"
    )
    s.append(f'<text x="{W / 2}" y="24" text-anchor="middle" fill="#8b93b0" font-size="14">Heat Exchanger ({flow})</text>')

    s.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="14" fill="#1a1d2e"/>')
    s.append(
        f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="14" fill="url(#shellG)" '
        'fill-opacity=".42" stroke="#3a4160" stroke-width="2"/>'
    )
    for ty in tube_ys:
        s.append(
            f'<rect x="{x0 + 12}" y="{ty - 5}" width="{x1 - x0 - 24}" height="10" rx="5" '
            'fill="url(#tubeG)" stroke="#05070d" stroke-width="2.5"/>'
        )

    xs, xe = x0 + 16, x1 - 16
    dur_h = 9.0 / speed
    for _ in range(n_particles):
        y = rng.uniform(y0 + 14, y1 - 14)
        for _try in range(60):
            if all(abs(y - ty) > 11 for ty in tube_ys):
                break
            y = rng.uniform(y0 + 14, y1 - 14)
        p = rng.random()
        if animate:
            s.append(
                f'<circle cy="{y:.1f}" r="4.5" fill="url(#hotP)"><animate attributeName="cx" from="{xs}" to="{xe}" '
                f'dur="{dur_h:.2f}s" begin="-{p * dur_h:.2f}s" repeatCount="indefinite"/></circle>'
            )
        else:
            s.append(f'<circle cx="{xs + (xe - xs) * p:.1f}" cy="{y:.1f}" r="4.5" fill="url(#hotP)"/>')

    dur_c = 6.0 / speed
    for i, ty in enumerate(tube_ys):
        for k in range(3):
            p = (k / 3.0 + i * 0.37) % 1.0
            a, b = (xe, xs) if counter else (xs, xe)
            if animate:
                s.append(
                    f'<circle cy="{ty}" r="2" fill="#fff"><animate attributeName="cx" from="{a}" to="{b}" '
                    f'dur="{dur_c:.2f}s" begin="-{p * dur_c:.2f}s" repeatCount="indefinite"/></circle>'
                )
            else:
                s.append(f'<circle cx="{a + (b - a) * p:.1f}" cy="{ty}" r="2" fill="#fff"/>')

    hot_in, cold_in, cold_out, hot_out = "#ff6b5e", "#38bdf8", "#7dd3fc", "#ff9a6b"
    ya, yb, yc = 62, 143, 236
    s.append(label(146, ya, "end", hot_in, f"Hot in {fmt(Thi)}{tu}") + arrow(154, 182, ya, hot_in))
    if counter:
        s.append(label(146, yb, "end", cold_out, f"Cold out {fmt(Tco)}{tu}") + arrow(182, 154, yb, cold_out))
        s.append(label(856, yb, "start", cold_in, f"{fmt(Tci)}{tu} Cold in") + arrow(846, 818, yb, cold_in))
    else:
        s.append(label(146, yb, "end", cold_in, f"Cold in {fmt(Tci)}{tu}") + arrow(154, 182, yb, cold_in))
        s.append(label(856, yb, "start", cold_out, f"{fmt(Tco)}{tu} Cold out") + arrow(818, 846, yb, cold_out))
    s.append(label(856, yc, "start", hot_out, f"{fmt(Tho)}{tu} Hot out") + arrow(818, 846, yc, hot_out))

    if show_legend:
        s.append('<circle cx="200" cy="278" r="4" fill="#ef5350"/>')
        s.append('<text x="210" y="283" fill="#ef5350" font-size="13" font-weight="700">Hot fluid</text>')
        s.append('<circle cx="298" cy="278" r="4" fill="#42a5f5"/>')
        s.append('<text x="308" y="283" fill="#42a5f5" font-size="13" font-weight="700">Cold fluid</text>')
        s.append(
            '<text x="710" y="268" text-anchor="middle" fill="#8b93b0" font-size="11" '
            'font-family="Consolas, monospace">fluid temperature</text>'
        )
        s.append('<rect x="610" y="273" width="200" height="10" rx="5" fill="url(#barG)"/>')
        s.append(f'<text x="610" y="296" fill="#8b93b0" font-size="11" font-family="Consolas, monospace">{fmt(lo)}{tu}</text>')
        s.append(
            f'<text x="810" y="296" text-anchor="end" fill="#8b93b0" font-size="11" '
            f'font-family="Consolas, monospace">{fmt(hi)}{tu}</text>'
        )
    s.append("</svg>")
    return "".join(s)


def chart_svg(flow, Thi, Tho, Tci, Tco, tu, show_grid):
    W, H = 1000, 330
    L, R, T, B = 100, 960, 16, 262
    counter = flow == "Counter Flow"
    vals = [Thi, Tho, Tci, Tco]
    ymin, ymax = min(vals) - 10, max(vals) + 10

    def Y(v):
        return B - (v - ymin) / (ymax - ymin) * (B - T)

    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">']
    for i in range(5):
        t = ymin + (ymax - ymin) * i / 4
        if show_grid:
            s.append(f'<line x1="{L}" x2="{R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="#1f2438" stroke-width="1"/>')
        s.append(
            f'<text x="{L - 12}" y="{Y(t) + 4:.1f}" text-anchor="end" fill="#6f7ba3" font-size="12" '
            f'font-family="Consolas, monospace">{t:.0f}</text>'
        )
    s.append(f'<line x1="{L}" x2="{R}" y1="{B}" y2="{B}" stroke="#2a2f48" stroke-width="1.5"/>')
    cold_left, cold_right = (Tco, Tci) if counter else (Tci, Tco)
    s.append(f'<line x1="{L}" y1="{Y(Thi):.1f}" x2="{R}" y2="{Y(Tho):.1f}" stroke="#ef5350" stroke-width="4" stroke-linecap="round"/>')
    s.append(f'<line x1="{L}" y1="{Y(cold_left):.1f}" x2="{R}" y2="{Y(cold_right):.1f}" stroke="#42a5f5" stroke-width="4" stroke-linecap="round"/>')
    s.append(
        f'<text transform="translate(34 {(T + B) / 2}) rotate(-90)" text-anchor="middle" fill="#6f7ba3" '
        f'font-size="13">Temperature ({tu})</text>'
    )
    s.append(f'<text x="{(L + R) / 2}" y="{B + 34}" text-anchor="middle" fill="#6f7ba3" font-size="13">Position along exchanger</text>')
    s.append("</svg>")
    return "".join(s)


SCENE_CSS = """
html, body { margin: 0; background: transparent; font-family: 'Segoe UI', Inter, system-ui, sans-serif; }
.wrap { max-width: 1100px; margin: 0 auto; }
svg { width: 100%; height: auto; display: block; }
.pill {
    width: max-content; margin: -4px auto 0 auto; padding: 9px 20px; border-radius: 12px;
    background: #0d1020; border: 1px solid #2c3250; box-shadow: 0 4px 18px rgba(0,0,0,.35);
    font-family: 'Times New Roman', serif; font-size: 21px; font-weight: 600; color: #f1f3fb;
}
.pill .q { color: #facc15; } .pill .lm { color: #38bdf8; } .pill .qv { color: #ef4444; }
.pill .dim { color: #cfd4e8; }
"""

d = dict(flow=flow_type, Thi=tconv(T_h_in), Tho=tconv(T_h_out), Tci=tconv(T_c_in), Tco=tconv(T_c_out), tu=tu)
pill_html = ""
if show_pill:
    u_d = CONV["U"][units][0](U)
    a_d = CONV["A"][units][0](Area)
    pill_html = (
        '<div class="pill"><span class="q">Q</span> <span class="dim">=</span> UA ΔT<sub>lm</sub> '
        f'&nbsp;<span class="dim">=</span>&nbsp; {u_d:g} <span class="dim">×</span> {a_d:.4g} '
        f'<span class="dim">×</span> <span class="lm">{dconv(LMTD):.1f}</span> &nbsp;<span class="dim">=</span>&nbsp; '
        f'<span class="qv">{q_txt} {q_unit}</span></div>'
    )

scene = (
    f"<style>{SCENE_CSS}</style><div class='wrap'>"
    + exchanger_svg(n_tubes=n_tubes, n_particles=n_particles, speed=speed, animate=animate,
                    show_legend=show_legend, **d)
    + chart_svg(show_grid=show_grid, **d)
    + pill_html
    + "</div>"
)
with scene_slot.container():
    components.html(scene, height=790, scrolling=False)