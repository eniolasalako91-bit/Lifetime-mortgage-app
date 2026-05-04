import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Lifetime Mortgage Decision Model", layout="wide")

# ==========================================================
# HELPERS
# ==========================================================

def gbp(x):
    return f"£{x:,.0f}"

def present_value(fv, r, t):
    return fv / ((1 + r/100)**t)

def display_value(v, years, r, view):
    if view == "Nominal":
        return gbp(v)
    elif view == "Present Value":
        return gbp(present_value(v, r, years))
    else:
        return f"{gbp(v)} / {gbp(present_value(v, r, years))}"

# ==========================================================
# MODEL
# ==========================================================

def model(current_value, release_pct, rate, growth, years):
    future_value = current_value * ((1 + growth/100)**years)
    loan = current_value * (release_pct/100)
    debt = loan * ((1 + rate/100)**years)

    debt_capped = min(debt, future_value)

    equity = future_value - debt_capped

    return future_value, debt, equity

# ==========================================================
# HEADER
# ==========================================================

st.title("Lifetime Mortgage Decision App")

# ==========================================================
# INFORMATION REEL
# ==========================================================

st.subheader("Information Reel")

info_options = [
    "1 of 4: Scenario-based tool",
    "2 of 4: Not financial advice",
    "3 of 4: No negative equity protection",
    "4 of 4: Tax-free cash note"
]

selected_info = st.select_slider(
    "Slide through key notices",
    options=info_options
)

st.caption(f"Currently showing: {selected_info}")

if selected_info.startswith("1"):
    st.info("This tool provides scenario-based comparisons using assumptions.")

elif selected_info.startswith("2"):
    st.warning("This is not financial advice.")

elif selected_info.startswith("3"):
    st.info("No negative equity: repayment capped at property value.")

else:
    st.info("Equity release cash is generally tax-free.")

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.header("Inputs")

property_value = st.sidebar.number_input("Property value", value=200000)
release_pct = st.sidebar.slider("Equity release %", 0, 100, 30)
interest_rate = st.sidebar.slider("Interest rate %", 0.0, 15.0, 5.0)
growth_rate = st.sidebar.slider("Property growth %", -5.0, 10.0, 2.0)
years = st.sidebar.slider("Years", 1, 30, 15)

# valuation view
view = st.sidebar.selectbox(
    "View type",
    ["Nominal", "Present Value", "Both"]
)

discount_rate = st.sidebar.slider("Discount rate %", 0.0, 10.0, 3.0)

# ==========================================================
# CALCULATION
# ==========================================================

future_value, debt, equity = model(
    property_value,
    release_pct,
    interest_rate,
    growth_rate,
    years
)

# ==========================================================
# OUTPUTS
# ==========================================================

st.subheader("Key Results")

col1, col2, col3 = st.columns(3)

col1.metric("Future Property Value", display_value(future_value, years, discount_rate, view))
col2.metric("Debt at Sale", display_value(debt, years, discount_rate, view))
col3.metric("Remaining Equity", display_value(equity, years, discount_rate, view))

# ==========================================================
# CHART
# ==========================================================

st.subheader("Time Comparison")

data = []

for y in range(1, years+1):
    fv, d, e = model(property_value, release_pct, interest_rate, growth_rate, y)

    data.append({
        "Year": y,
        "Property": fv,
        "Debt": d,
        "Equity": e,
        "Property PV": present_value(fv, discount_rate, y),
        "Debt PV": present_value(d, discount_rate, y),
        "Equity PV": present_value(e, discount_rate, y)
    })

df = pd.DataFrame(data)

fig, ax = plt.subplots()

if view == "Present Value":
    ax.plot(df["Year"], df["Equity PV"], label="Equity (PV)")
else:
    ax.plot(df["Year"], df["Equity"], label="Equity")

ax.set_title("Equity over time")
ax.legend()

st.pyplot(fig)

# ==========================================================
# TABLE
# ==========================================================

st.subheader("Detailed Table")

if view == "Nominal":
    st.dataframe(df[["Year","Property","Debt","Equity"]])
elif view == "Present Value":
    st.dataframe(df[["Year","Property PV","Debt PV","Equity PV"]])
else:
    st.dataframe(df)

# ==========================================================
# PDF
# ==========================================================

def pdf_report():
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    c.drawString(50, 800, "Lifetime Mortgage Report")

    c.drawString(50, 760, f"Property value: {gbp(property_value)}")
    c.drawString(50, 740, f"Equity: {gbp(equity)}")

    c.drawString(50, 100, "Built with AI assistance")

    c.save()
    buffer.seek(0)
    return buffer

st.download_button(
    "Download PDF",
    data=pdf_report(),
    file_name="report.pdf"
)

# ==========================================================
# FOOTER
# ==========================================================

st.markdown("---")
st.caption("© 2026. ES. Lifetime Mortgage Financial Decision model. Built with AI assistance.")
