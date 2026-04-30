import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


def gbp(value):
    return f"£{value:,.0f}"


def calculate_model(
    original_mortgage,
    mortgage_paid_percent,
    current_property_value,
    equity_release_percent,
    annual_interest_rate,
    property_growth_rate,
    years,
    interest_mode,
    release_basis
):
    remaining_mortgage = original_mortgage * ((100 - mortgage_paid_percent) / 100)
    client_ownership_value_now = current_property_value * (mortgage_paid_percent / 100)

    if release_basis == "Full property value":
        release_base = current_property_value
    else:
        release_base = client_ownership_value_now

    equity_released = release_base * (equity_release_percent / 100)
    net_cash_now = equity_released - remaining_mortgage

    future_property_value = current_property_value * ((1 + property_growth_rate / 100) ** years)

    if interest_mode == "Rolled-up / compounded":
        debt_at_sale = equity_released * ((1 + annual_interest_rate / 100) ** years)
        monthly_interest_payment = 0
        total_interest_paid = 0
    else:
        debt_at_sale = equity_released
        monthly_interest_payment = (equity_released * (annual_interest_rate / 100)) / 12
        total_interest_paid = monthly_interest_payment * 12 * years

    debt_after_cap = min(debt_at_sale, future_property_value)
    remaining_equity_at_sale = max(0, future_property_value - debt_after_cap)

    total_client_position = remaining_equity_at_sale + net_cash_now - total_interest_paid
    no_release_position = future_property_value - remaining_mortgage
    difference_vs_no_release = total_client_position - no_release_position

    return {
        "remaining_mortgage": remaining_mortgage,
        "client_ownership_value_now": client_ownership_value_now,
        "release_base": release_base,
        "equity_released": equity_released,
        "net_cash_now": net_cash_now,
        "future_property_value": future_property_value,
        "debt_at_sale": debt_at_sale,
        "debt_after_cap": debt_after_cap,
        "monthly_interest_payment": monthly_interest_payment,
        "total_interest_paid": total_interest_paid,
        "remaining_equity_at_sale": remaining_equity_at_sale,
        "total_client_position": total_client_position,
        "no_release_position": no_release_position,
        "difference_vs_no_release": difference_vs_no_release
    }


def insight_message(result, years, property_growth_rate, interest_mode):
    net_cash = result["net_cash_now"]
    debt = result["debt_at_sale"]
    future_value = result["future_property_value"]
    equity = result["remaining_equity_at_sale"]
    diff = result["difference_vs_no_release"]

    if diff < 0:
        decision_text = (
            f"This gives {gbp(net_cash)} now, but leaves you {gbp(abs(diff))} worse off vs no release."
        )
    else:
        decision_text = (
            f"This gives {gbp(net_cash)} now and leaves you {gbp(diff)} better off vs no release."
        )

    if interest_mode == "Rolled-up / compounded":
        interest_text = "Debt grows over time (no monthly payments)."
    else:
        interest_text = "Interest is paid monthly (reduces future debt growth)."

    return (
        f"After {years} years at {property_growth_rate}% growth, "
        f"property ≈ {gbp(future_value)}, debt ≈ {gbp(debt)}, "
        f"equity ≈ {gbp(equity)}. {interest_text} {decision_text}"
    )


# --- UI ---

st.set_page_config(page_title="Lifetime Mortgage Model", layout="wide")

st.title("Lifetime Mortgage Decision Model")

st.sidebar.header("Inputs")

original_mortgage = st.sidebar.number_input("Original mortgage (£)", value=100000)
mortgage_paid_percent = st.sidebar.number_input("Paid (%)", value=70.0)
current_property_value = st.sidebar.number_input("Property value (£)", value=200000)
equity_release_percent = st.sidebar.number_input("Release (%)", value=30.0)
annual_interest_rate = st.sidebar.number_input("Interest (%)", value=5.0)
years = st.sidebar.number_input("Years", value=15)
property_growth_rate = st.sidebar.number_input("Growth (%)", value=2.0)

interest_mode = st.sidebar.selectbox(
    "Interest type",
    ["Rolled-up / compounded", "Interest paid monthly"]
)

release_basis = st.sidebar.selectbox(
    "Release basis",
    ["Full property value", "Client ownership value only"]
)

result = calculate_model(
    original_mortgage,
    mortgage_paid_percent,
    current_property_value,
    equity_release_percent,
    annual_interest_rate,
    property_growth_rate,
    years,
    interest_mode,
    release_basis
)

st.subheader("Key Results")

col1, col2, col3 = st.columns(3)

col1.metric("Cash now", gbp(result["net_cash_now"]))
col2.metric("Debt at sale", gbp(result["debt_at_sale"]))
col3.metric("Remaining equity", gbp(result["remaining_equity_at_sale"]))

st.subheader("Insight")
st.info(insight_message(result, years, property_growth_rate, interest_mode))

# --- Chart ---

df = pd.DataFrame({
    "Metric": ["Debt", "Equity"],
    "Value": [result["debt_at_sale"], result["remaining_equity_at_sale"]]
})

fig, ax = plt.subplots()
ax.bar(df["Metric"], df["Value"])
ax.set_title("Outcome at Sale")
st.pyplot(fig)
