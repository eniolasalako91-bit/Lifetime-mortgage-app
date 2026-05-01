import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Lifetime Mortgage Decision Model",
    layout="wide"
)

# ==========================================================
# HELPERS
# ==========================================================

def gbp(value):
    return f"£{value:,.0f}"


def explain(title, text):
    with st.expander(f"ℹ️ {title}"):
        st.write(text)


# ==========================================================
# CORE MODEL
# ==========================================================

def calculate_model(
    original_mortgage,
    mortgage_paid_percent,
    current_property_value,
    equity_release_percent,
    annual_interest_rate,
    property_growth_rate,
    years,
    interest_mode,
    release_basis,
):
    remaining_mortgage = original_mortgage * ((100 - mortgage_paid_percent) / 100)
    client_ownership_value_now = current_property_value * (mortgage_paid_percent / 100)

    release_base = (
        current_property_value
        if release_basis == "Full property value"
        else client_ownership_value_now
    )

    equity_released = release_base * (equity_release_percent / 100)
    net_cash_now = equity_released - remaining_mortgage

    future_property_value = current_property_value * ((1 + property_growth_rate / 100) ** years)

    erc_share_at_disposal = future_property_value * (equity_release_percent / 100)

    if interest_mode == "Interest paid monthly":
        monthly_interest_payment = (equity_released * (annual_interest_rate / 100)) / 12
        total_interest_paid = monthly_interest_payment * 12 * years
        rolled_up_interest = 0
        amount_due_to_erc = erc_share_at_disposal
    else:
        monthly_interest_payment = 0
        total_interest_paid = 0
        rolled_up_interest = equity_released * ((1 + annual_interest_rate / 100) ** years) - equity_released
        amount_due_to_erc = erc_share_at_disposal + rolled_up_interest

    amount_due_after_cap = min(amount_due_to_erc, future_property_value)
    remaining_equity_at_sale = max(0, future_property_value - amount_due_after_cap)

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
        "erc_share_at_disposal": erc_share_at_disposal,
        "rolled_up_interest": rolled_up_interest,
        "amount_due_to_erc": amount_due_to_erc,
        "amount_due_after_cap": amount_due_after_cap,
        "monthly_interest_payment": monthly_interest_payment,
        "total_interest_paid": total_interest_paid,
        "remaining_equity_at_sale": remaining_equity_at_sale,
        "total_client_position": total_client_position,
        "no_release_position": no_release_position,
        "difference_vs_no_release": difference_vs_no_release,
    }


def insight_message(result, years, property_growth_rate, interest_mode):
    if interest_mode == "Interest paid monthly":
        interest_text = (
            "Because interest is paid monthly, the Equity Release Council receives only its agreed "
            "percentage share of the property disposal value."
        )
    else:
        interest_text = (
            "Because interest is not paid monthly, unpaid interest builds up and is added to the "
            "Equity Release Council’s share at disposal."
        )

    diff = result["difference_vs_no_release"]

    if diff < 0:
        comparison_text = (
            f"The projected client position is {gbp(abs(diff))} lower than the no-release option."
        )
    else:
        comparison_text = (
            f"The projected client position is {gbp(diff)} higher than the no-release option."
        )

    return (
        f"After {years} years, assuming property growth of {property_growth_rate}% per year, "
        f"the property may be worth {gbp(result['future_property_value'])}. "
        f"The Equity Release Council share at disposal is {gbp(result['erc_share_at_disposal'])}. "
        f"The total amount due at sale is {gbp(result['amount_due_to_erc'])}. "
        f"{interest_text} {comparison_text}"
    )


# ==========================================================
# APP HEADER
# ==========================================================

st.title("Lifetime Mortgage Financial Decision Model")

st.write(
    "This app models lifetime mortgage outcomes by comparing property growth, equity release percentage, "
    "time to disposal, and whether interest is paid monthly or rolled up."
)

st.warning(
    "This is a decision-support tool only. It is not financial advice. "
    "Users should seek independent regulated financial advice before making decisions."
)

# ==========================================================
# SIDEBAR INPUTS
# ==========================================================

st.sidebar.header("Preset")

preset = st.sidebar.selectbox(
    "Choose starting example",
    [
        "Custom",
        "Case Study 1 - 50% Release",
        "Case Study 2 - 20% Release"
    ]
)

if preset == "Case Study 1 - 50% Release":
    default_original_mortgage = 100000
    default_paid_percent = 70.0
    default_current_value = 200000
    default_release_percent = 50.0
elif preset == "Case Study 2 - 20% Release":
    default_original_mortgage = 100000
    default_paid_percent = 70.0
    default_current_value = 200000
    default_release_percent = 20.0
else:
    default_original_mortgage = 100000
    default_paid_percent = 70.0
    default_current_value = 200000
    default_release_percent = 30.0

st.sidebar.header("Client Inputs")

original_mortgage = st.sidebar.number_input(
    "Original mortgage / acquisition price (£)",
    min_value=0,
    value=default_original_mortgage,
    step=5000
)

mortgage_paid_percent = st.sidebar.number_input(
    "Mortgage already paid (%)",
    min_value=0.0,
    max_value=100.0,
    value=default_paid_percent,
    step=1.0
)

current_property_value = st.sidebar.number_input(
    "Current property value (£)",
    min_value=1,
    value=default_current_value,
    step=5000
)

equity_release_percent = st.sidebar.number_input(
    "Equity release percentage / ERC share (%)",
    min_value=0.0,
    max_value=100.0,
    value=default_release_percent,
    step=1.0
)

annual_interest_rate = st.sidebar.number_input(
    "Annual interest rate (%)",
    min_value=0.0,
    max_value=25.0,
    value=5.0,
    step=0.1
)

years = st.sidebar.number_input(
    "Years until sale / care / death",
    min_value=1,
    max_value=50,
    value=15,
    step=1
)

property_growth_rate = st.sidebar.number_input(
    "Property growth assumption (%)",
    min_value=-10.0,
    max_value=20.0,
    value=2.0,
    step=0.1
)

interest_mode = st.sidebar.selectbox(
    "Interest treatment",
    [
        "Interest not paid / rolled up",
        "Interest paid monthly"
    ]
)

release_basis = st.sidebar.selectbox(
    "Release calculation basis",
    [
        "Full property value",
        "Client ownership value only"
    ]
)

# ==========================================================
# MAIN CALCULATION
# ==========================================================

result = calculate_model(
    original_mortgage,
    mortgage_paid_percent,
    current_property_value,
    equity_release_percent,
    annual_interest_rate,
    property_growth_rate,
    years,
    interest_mode,
    release_basis,
)

# ==========================================================
# KEY OUTPUTS WITH INFO SECTIONS
# ==========================================================

st.subheader("Key Outputs")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Net cash now", gbp(result["net_cash_now"]))
col2.metric("ERC share at disposal", gbp(result["erc_share_at_disposal"]))
col3.metric("Amount due to ERC", gbp(result["amount_due_to_erc"]))
col4.metric("Remaining equity", gbp(result["remaining_equity_at_sale"]))

explain(
    "Net cash now",
    "This is the cash the client receives now after using part of the equity release to clear any remaining mortgage balance."
)

explain(
    "ERC share at disposal",
    "This is the Equity Release Council/lender side’s agreed percentage share of the property value when the property is sold."
)

explain(
    "Amount due to ERC",
    "This is the total amount payable to the equity release side at sale. If interest is paid monthly, this is normally just the agreed share of the sale value. If interest is not paid, rolled-up interest is added."
)

explain(
    "Remaining equity",
    "This is the estimated amount left for the client from the property after the equity release side has been repaid at sale."
)

# ==========================================================
# INSIGHT
# ==========================================================

st.subheader("Decision Insight")
st.info(insight_message(result, years, property_growth_rate, interest_mode))

explain(
    "Decision insight",
    "This section explains the main trade-off in plain language: what the client receives now, what may be due at sale, and how paying or not paying interest changes the final outcome."
)

# ==========================================================
# DETAILED BREAKDOWN
# ==========================================================

st.subheader("Detailed Breakdown")

breakdown = pd.DataFrame({
    "Item": [
        "Original mortgage",
        "Remaining mortgage",
        "Client ownership value now",
        "Release base",
        "Equity released",
        "Net cash now",
        "Future property value",
        "ERC share at disposal",
        "Rolled-up unpaid interest",
        "Amount due to ERC",
        "Amount due after no-negative-equity cap",
        "Monthly interest payment",
        "Total interest paid during term",
        "Remaining equity at sale",
        "Total client position",
        "No-release position",
        "Difference vs no release"
    ],
    "Value": [
        original_mortgage,
        result["remaining_mortgage"],
        result["client_ownership_value_now"],
        result["release_base"],
        result["equity_released"],
        result["net_cash_now"],
        result["future_property_value"],
        result["erc_share_at_disposal"],
        result["rolled_up_interest"],
        result["amount_due_to_erc"],
        result["amount_due_after_cap"],
        result["monthly_interest_payment"],
        result["total_interest_paid"],
        result["remaining_equity_at_sale"],
        result["total_client_position"],
        result["no_release_position"],
        result["difference_vs_no_release"]
    ]
})

st.dataframe(
    breakdown.style.format({"Value": "£{:,.0f}"}),
    use_container_width=True
)

explain(
    "Total client position",
    "This combines the cash received now, the amount left from the property at sale, and any interest paid during the period. It gives the client’s overall financial outcome."
)

explain(
    "Difference vs no release",
    "This compares the equity release outcome with the alternative of not taking equity release. A negative number means the client is financially worse off compared with no release, but may still benefit from cash received earlier."
)

# ==========================================================
# MULTIPLE FUTURES
# ==========================================================

st.subheader("Multiple Possible Futures")

growth_rates = sorted(set([
    -1.0,
    0.0,
    2.0,
    3.0,
    5.0,
    property_growth_rate
]))

scenario_rows = []

for growth in growth_rates:
    for mode in ["Interest not paid / rolled up", "Interest paid monthly"]:
        scenario = calculate_model(
            original_mortgage,
            mortgage_paid_percent,
            current_property_value,
            equity_release_percent,
            annual_interest_rate,
            growth,
            years,
            mode,
            release_basis,
        )

        scenario_rows.append({
            "Property growth": f"{growth:.1f}%",
            "Interest treatment": mode,
            "Future property value": scenario["future_property_value"],
            "ERC share at disposal": scenario["erc_share_at_disposal"],
            "Rolled-up interest": scenario["rolled_up_interest"],
            "Amount due to ERC": scenario["amount_due_to_erc"],
            "Monthly interest payment": scenario["monthly_interest_payment"],
            "Remaining equity": scenario["remaining_equity_at_sale"],
            "Difference vs no release": scenario["difference_vs_no_release"]
        })

scenario_df = pd.DataFrame(scenario_rows)

st.dataframe(
    scenario_df.style.format({
        "Future property value": "£{:,.0f}",
        "ERC share at disposal": "£{:,.0f}",
        "Rolled-up interest": "£{:,.0f}",
        "Amount due to ERC": "£{:,.0f}",
        "Monthly interest payment": "£{:,.0f}",
        "Remaining equity": "£{:,.0f}",
        "Difference vs no release": "£{:,.0f}"
    }),
    use_container_width=True
)

explain(
    "Multiple possible futures",
    "This table shows how the outcome changes under different property growth assumptions. It helps users see that the final result depends on both property value growth and interest treatment."
)

# ==========================================================
# INTEREST COMPARISON
# ==========================================================

st.subheader("Interest Paid Monthly vs Interest Rolled Up")

rolled = calculate_model(
    original_mortgage,
    mortgage_paid_percent,
    current_property_value,
    equity_release_percent,
    annual_interest_rate,
    property_growth_rate,
    years,
    "Interest not paid / rolled up",
    release_basis,
)

monthly = calculate_model(
    original_mortgage,
    mortgage_paid_percent,
    current_property_value,
    equity_release_percent,
    annual_interest_rate,
    property_growth_rate,
    years,
    "Interest paid monthly",
    release_basis,
)

comparison = pd.DataFrame({
    "Option": ["Interest not paid / rolled up", "Interest paid monthly"],
    "ERC share at disposal": [
        rolled["erc_share_at_disposal"],
        monthly["erc_share_at_disposal"]
    ],
    "Rolled-up interest": [
        rolled["rolled_up_interest"],
        monthly["rolled_up_interest"]
    ],
    "Amount due to ERC": [
        rolled["amount_due_to_erc"],
        monthly["amount_due_to_erc"]
    ],
    "Remaining equity": [
        rolled["remaining_equity_at_sale"],
        monthly["remaining_equity_at_sale"]
    ],
    "Total client position": [
        rolled["total_client_position"],
        monthly["total_client_position"]
    ],
})

st.dataframe(
    comparison.style.format({
        "ERC share at disposal": "£{:,.0f}",
        "Rolled-up interest": "£{:,.0f}",
        "Amount due to ERC": "£{:,.0f}",
        "Remaining equity": "£{:,.0f}",
        "Total client position": "£{:,.0f}"
    }),
    use_container_width=True
)

fig1, ax1 = plt.subplots()
ax1.bar(comparison["Option"], comparison["Amount due to ERC"])
ax1.set_title("Amount Due to Equity Release Council")
ax1.set_ylabel("Amount (£)")
st.pyplot(fig1)

fig2, ax2 = plt.subplots()
ax2.bar(comparison["Option"], comparison["Remaining equity"])
ax2.set_title("Remaining Equity at Disposal")
ax2.set_ylabel("Amount (£)")
st.pyplot(fig2)

explain(
    "Interest paid monthly vs interest rolled up",
    "If interest is paid monthly, the client makes regular payments and protects more of the property value at sale. If interest is not paid, it builds up and increases the amount due at sale."
)

# ==========================================================
# TIME IMPACT VIEW
# ==========================================================

st.subheader("Time Impact View")

time_rows = []

for year in range(1, years + 1):
    rolled_year = calculate_model(
        original_mortgage,
        mortgage_paid_percent,
        current_property_value,
        equity_release_percent,
        annual_interest_rate,
        property_growth_rate,
        year,
        "Interest not paid / rolled up",
        release_basis,
    )

    monthly_year = calculate_model(
        original_mortgage,
        mortgage_paid_percent,
        current_property_value,
        equity_release_percent,
        annual_interest_rate,
        property_growth_rate,
        year,
        "Interest paid monthly",
        release_basis,
    )

    time_rows.append({
        "Year": year,
        "Property value": rolled_year["future_property_value"],
        "ERC share": rolled_year["erc_share_at_disposal"],
        "Rolled-up amount due": rolled_year["amount_due_to_erc"],
        "Monthly-paid amount due": monthly_year["amount_due_to_erc"],
        "Rolled-up remaining equity": rolled_year["remaining_equity_at_sale"],
        "Monthly-paid remaining equity": monthly_year["remaining_equity_at_sale"],
    })

time_df = pd.DataFrame(time_rows)

fig3, ax3 = plt.subplots()
ax3.plot(time_df["Year"], time_df["Property value"], label="Property value")
ax3.plot(time_df["Year"], time_df["ERC share"], label="ERC share at disposal")
ax3.plot(time_df["Year"], time_df["Rolled-up amount due"], label="Amount due if interest not paid")
ax3.plot(time_df["Year"], time_df["Monthly-paid amount due"], label="Amount due if interest paid monthly")
ax3.set_title("Property Value and Amount Due Over Time")
ax3.set_xlabel("Years")
ax3.set_ylabel("Amount (£)")
ax3.legend()
st.pyplot(fig3)

fig4, ax4 = plt.subplots()
ax4.plot(time_df["Year"], time_df["Rolled-up remaining equity"], label="Interest not paid / rolled up")
ax4.plot(time_df["Year"], time_df["Monthly-paid remaining equity"], label="Interest paid monthly")
ax4.set_title("Remaining Equity Over Time")
ax4.set_xlabel("Years")
ax4.set_ylabel("Remaining equity (£)")
ax4.legend()
st.pyplot(fig4)

st.dataframe(
    time_df.style.format({
        "Property value": "£{:,.0f}",
        "ERC share": "£{:,.0f}",
        "Rolled-up amount due": "£{:,.0f}",
        "Monthly-paid amount due": "£{:,.0f}",
        "Rolled-up remaining equity": "£{:,.0f}",
        "Monthly-paid remaining equity": "£{:,.0f}",
    }),
    use_container_width=True
)

explain(
    "Time impact view",
    "This shows how the outcome changes year by year. It helps users understand how time, property growth, and interest treatment affect the final amount kept from the property."
)

# ==========================================================
# FINAL SUMMARY
# ==========================================================

st.subheader("Plain-English Summary")

st.write(
    """
    This model separates the repayment outcome into two parts:

    1. **Equity Release Council share at disposal**  
       This is based on the agreed percentage of the property value when the property is sold.

    2. **Interest treatment**  
       If the client pays interest monthly, the council receives only its agreed disposal share.  
       If the client does not pay interest monthly, unpaid interest rolls up and is added to the council's share.

    Therefore, the client’s final benefit depends on:
    - the property value at disposal,
    - the equity release percentage,
    - whether interest is paid monthly or rolled up,
    - and the number of years before disposal.
    """
)
