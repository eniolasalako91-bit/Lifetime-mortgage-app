import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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


def future_value_lump_sum(amount, annual_rate, years):
    return amount * ((1 + annual_rate / 100) ** years)


def future_value_annual_savings(annual_savings_list, annual_rate):
    total = 0
    total_years = len(annual_savings_list)

    for index, saving in enumerate(annual_savings_list):
        years_remaining = total_years - index - 1
        total += saving * ((1 + annual_rate / 100) ** years_remaining)

    return total


def calculate_mortgage_savings(
    remaining_mortgage,
    mortgage_interest_rate,
    years_until_sale
):
    if years_until_sale <= 0 or remaining_mortgage <= 0:
        return {
            "mortgage_principal_paid_until_sale": 0,
            "mortgage_interest_paid_until_sale": 0,
            "annual_principal_savings": [],
            "annual_interest_savings": [],
            "annual_total_savings": []
        }

    annual_principal_payment = remaining_mortgage / years_until_sale
    outstanding_balance = remaining_mortgage

    annual_principal_savings = []
    annual_interest_savings = []
    annual_total_savings = []

    for _ in range(years_until_sale):
        annual_interest = outstanding_balance * (mortgage_interest_rate / 100)

        annual_principal_savings.append(annual_principal_payment)
        annual_interest_savings.append(annual_interest)
        annual_total_savings.append(annual_principal_payment + annual_interest)

        outstanding_balance = max(0, outstanding_balance - annual_principal_payment)

    return {
        "mortgage_principal_paid_until_sale": sum(annual_principal_savings),
        "mortgage_interest_paid_until_sale": sum(annual_interest_savings),
        "annual_principal_savings": annual_principal_savings,
        "annual_interest_savings": annual_interest_savings,
        "annual_total_savings": annual_total_savings
    }


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
    mortgage_interest_rate,
    investment_return_rate,
    invest_cash_balance,
    invest_mortgage_savings,
    invest_sell_now_cash
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

    equity_lender_share_at_disposal = future_property_value * (equity_release_percent / 100)

    if interest_mode == "Interest paid monthly":
        monthly_interest_payment = (equity_released * (annual_interest_rate / 100)) / 12
        total_interest_paid = monthly_interest_payment * 12 * years
        rolled_up_interest = 0
        amount_due_to_equity_lender = equity_lender_share_at_disposal
    else:
        monthly_interest_payment = 0
        total_interest_paid = 0
        rolled_up_interest = equity_released * ((1 + annual_interest_rate / 100) ** years) - equity_released
        amount_due_to_equity_lender = equity_lender_share_at_disposal + rolled_up_interest

    amount_due_after_cap = min(amount_due_to_equity_lender, future_property_value)
    remaining_equity_at_sale = max(0, future_property_value - amount_due_after_cap)

    mortgage_savings = calculate_mortgage_savings(
        remaining_mortgage=remaining_mortgage,
        mortgage_interest_rate=mortgage_interest_rate,
        years_until_sale=years
    )

    mortgage_principal_saved_until_sale = mortgage_savings["mortgage_principal_paid_until_sale"]
    mortgage_interest_paid_until_sale = mortgage_savings["mortgage_interest_paid_until_sale"]

    if invest_cash_balance == "Yes":
        future_value_of_cash_balance = future_value_lump_sum(
            max(0, net_cash_now),
            investment_return_rate,
            years
        )
    else:
        future_value_of_cash_balance = max(0, net_cash_now)

    if invest_mortgage_savings == "Yes":
        future_value_of_mortgage_savings = future_value_annual_savings(
            mortgage_savings["annual_total_savings"],
            investment_return_rate
        )
    else:
        future_value_of_mortgage_savings = sum(mortgage_savings["annual_total_savings"])

    total_client_position = (
        remaining_equity_at_sale
        + future_value_of_cash_balance
        + future_value_of_mortgage_savings
        - total_interest_paid
    )

    no_equity_release_position = (
        future_property_value
        - mortgage_interest_paid_until_sale
    )

    sell_now_cash = current_property_value - remaining_mortgage

    if invest_sell_now_cash == "Yes":
        future_value_sell_now_cash = future_value_lump_sum(
            sell_now_cash,
            investment_return_rate,
            years
        )
    else:
        future_value_sell_now_cash = sell_now_cash

    difference_vs_no_equity_release = total_client_position - no_equity_release_position
    difference_vs_sell_now = total_client_position - future_value_sell_now_cash

    return {
        "remaining_mortgage": remaining_mortgage,
        "client_ownership_value_now": client_ownership_value_now,
        "release_base": release_base,
        "equity_released": equity_released,
        "net_cash_now": net_cash_now,
        "future_property_value": future_property_value,
        "equity_lender_share_at_disposal": equity_lender_share_at_disposal,
        "rolled_up_interest": rolled_up_interest,
        "amount_due_to_equity_lender": amount_due_to_equity_lender,
        "amount_due_after_cap": amount_due_after_cap,
        "monthly_interest_payment": monthly_interest_payment,
        "total_interest_paid": total_interest_paid,
        "remaining_equity_at_sale": remaining_equity_at_sale,
        "mortgage_principal_saved_until_sale": mortgage_principal_saved_until_sale,
        "mortgage_interest_paid_until_sale": mortgage_interest_paid_until_sale,
        "future_value_of_cash_balance": future_value_of_cash_balance,
        "future_value_of_mortgage_savings": future_value_of_mortgage_savings,
        "total_client_position": total_client_position,
        "no_equity_release_position": no_equity_release_position,
        "sell_now_cash": sell_now_cash,
        "future_value_sell_now_cash": future_value_sell_now_cash,
        "difference_vs_no_equity_release": difference_vs_no_equity_release,
        "difference_vs_sell_now": difference_vs_sell_now,
        "annual_total_savings": mortgage_savings["annual_total_savings"],
    }


def insight_message(result, years, property_growth_rate, interest_mode):
    if interest_mode == "Interest paid monthly":
        interest_text = (
            "Because interest is paid monthly, the Equity Lender receives only its agreed "
            "percentage share of the property disposal value."
        )
    else:
        interest_text = (
            "Because interest is not paid monthly, unpaid interest builds up and is added to the "
            "Equity Lender’s share at disposal."
        )

    diff = result["difference_vs_no_equity_release"]

    if diff < 0:
        comparison_text = (
            f"The projected client position is {gbp(abs(diff))} lower than the no-equity-release option."
        )
    else:
        comparison_text = (
            f"The projected client position is {gbp(diff)} higher than the no-equity-release option."
        )

    return (
        f"After {years} years, assuming property growth of {property_growth_rate}% per year, "
        f"the property may be worth {gbp(result['future_property_value'])}. "
        f"The Equity Lender share at disposal is {gbp(result['equity_lender_share_at_disposal'])}. "
        f"The total amount due at sale is {gbp(result['amount_due_to_equity_lender'])}. "
        f"{interest_text} {comparison_text}"
    )


# ==========================================================
# PDF REPORT
# ==========================================================

def create_pdf_report(result, inputs):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Lifetime Mortgage Decision Report")

    y -= 25
    pdf.setFont("Helvetica", 9)
    pdf.drawString(50, y, "This report is for decision-support only and is not financial advice.")

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Inputs")

    pdf.setFont("Helvetica", 9)
    for key, value in inputs.items():
        y -= 16
        pdf.drawString(50, y, f"{key}: {value}")

    y -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Key Results")

    report_items = {
        "Cash received now": gbp(result["net_cash_now"]),
        "Future property value": gbp(result["future_property_value"]),
        "Equity Lender share at disposal": gbp(result["equity_lender_share_at_disposal"]),
        "Rolled-up interest": gbp(result["rolled_up_interest"]),
        "Amount due to Equity Lender": gbp(result["amount_due_to_equity_lender"]),
        "Remaining equity at sale": gbp(result["remaining_equity_at_sale"]),
        "Future value of cash balance": gbp(result["future_value_of_cash_balance"]),
        "Future value of mortgage savings": gbp(result["future_value_of_mortgage_savings"]),
        "Total client position": gbp(result["total_client_position"]),
        "No-equity-release position": gbp(result["no_equity_release_position"]),
        "Sell-now position": gbp(result["future_value_sell_now_cash"]),
        "Difference vs no equity release": gbp(result["difference_vs_no_equity_release"]),
    }

    pdf.setFont("Helvetica", 9)
    for key, value in report_items.items():
        y -= 16
        if y < 80:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 9)
        pdf.drawString(50, y, f"{key}: {value}")

    y -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Important Notes")

    notes = [
        "This tool provides scenario-based comparisons using user-defined assumptions.",
        "Actual outcomes may differ due to market conditions, interest rate changes, property performance, and individual circumstances.",
        "Equity release cash is generally tax-free because it is treated as borrowing against the home, not income.",
        "No negative equity protection: repayment is capped at the property value in this model.",
        "The sell-now comparison excludes capital gains tax, estate agency fees, legal fees, moving costs, and other sale-related costs.",
    ]

    pdf.setFont("Helvetica", 8)
    for note in notes:
        y -= 14
        if y < 80:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 8)
        pdf.drawString(50, y, f"- {note}")

    pdf.save()
    buffer.seek(0)
    return buffer


# ==========================================================
# APP HEADER
# ==========================================================

st.title("Lifetime Mortgage Financial Decision Model")

st.write(
    "This app models lifetime mortgage outcomes by comparing property growth, equity release percentage, "
    "time to disposal, interest treatment, mortgage-payment savings, investment assumptions, and the option to sell now."
)

st.info(
    "This tool provides scenario-based comparisons using user-defined assumptions. "
    "Actual outcomes may differ due to market conditions, interest rate changes, property performance, "
    "and individual financial circumstances."
)

st.warning(
    "This is a decision-support tool only. It is not financial advice. "
    "Users should seek independent regulated financial advice before making decisions."
)

st.info(
    "No negative equity protection: if the property value falls and the amount due becomes greater than the property value, "
    "the homeowner or estate will not owe more than the property is worth. This model caps repayment at the property value."
)

st.info(
    "Equity release cash is generally tax-free because it is treated as borrowing against the home, not income. "
    "However, tax may apply depending on how the money is later used or invested."
)

# ==========================================================
# SIDEBAR INPUTS
# ==========================================================

st.sidebar.header("Preset")

preset = st.sidebar.selectbox(
    "Choose starting example",
    ["Custom", "Case Study 1 - 50% Release", "Case Study 2 - 20% Release"]
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

original_mortgage = st.sidebar.number_input("Original mortgage / acquisition price (£)", min_value=0, value=default_original_mortgage, step=5000)
mortgage_paid_percent = st.sidebar.number_input("Mortgage already paid (%)", min_value=0.0, max_value=100.0, value=default_paid_percent, step=1.0)
current_property_value = st.sidebar.number_input("Current property value (£)", min_value=1, value=default_current_value, step=5000)
equity_release_percent = st.sidebar.number_input("Equity release percentage / Equity Lender share (%)", min_value=0.0, max_value=100.0, value=default_release_percent, step=1.0)
annual_interest_rate = st.sidebar.number_input("Equity release annual interest rate (%)", min_value=0.0, max_value=25.0, value=5.0, step=0.1)
years = st.sidebar.number_input("Years until sale / care / death", min_value=1, max_value=50, value=15, step=1)
property_growth_rate = st.sidebar.number_input("Property growth assumption (%)", min_value=-10.0, max_value=20.0, value=2.0, step=0.1)

interest_mode = st.sidebar.selectbox(
    "Equity release interest treatment",
    ["Interest not paid / rolled up", "Interest paid monthly"]
)

release_basis = st.sidebar.selectbox(
    "Release calculation basis",
    ["Full property value", "Client ownership value only"]
)

st.sidebar.header("Opportunity Benefit Inputs")

mortgage_interest_rate = st.sidebar.number_input(
    "Existing mortgage interest rate (%)",
    min_value=0.0,
    max_value=25.0,
    value=5.0,
    step=0.1
)

investment_option = st.sidebar.selectbox(
    "Investment return assumption",
    [
        "0% - Not invested",
        "Custom rate",
        "S&P 500 style average",
        "Treasury bill style conservative rate",
        "Sovereign bond style conservative rate"
    ]
)

if investment_option == "0% - Not invested":
    investment_return_rate = 0.0
elif investment_option == "S&P 500 style average":
    investment_return_rate = 7.0
elif investment_option == "Treasury bill style conservative rate":
    investment_return_rate = 4.0
elif investment_option == "Sovereign bond style conservative rate":
    investment_return_rate = 3.0
else:
    investment_return_rate = st.sidebar.number_input(
        "Custom investment return rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=5.0,
        step=0.5
    )

invest_cash_balance = st.sidebar.selectbox("Invest remaining cash balance?", ["No", "Yes"])
invest_mortgage_savings = st.sidebar.selectbox("Invest mortgage payment savings?", ["No", "Yes"])
invest_sell_now_cash = st.sidebar.selectbox("Invest cash from selling property now?", ["No", "Yes"])

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
    mortgage_interest_rate,
    investment_return_rate,
    invest_cash_balance,
    invest_mortgage_savings,
    invest_sell_now_cash
)

# ==========================================================
# KEY OUTPUTS
# ==========================================================

st.subheader("Key Outputs")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Cash received now", gbp(result["net_cash_now"]))
col2.metric("Amount due to Equity Lender", gbp(result["amount_due_to_equity_lender"]))
col3.metric("Remaining equity at sale", gbp(result["remaining_equity_at_sale"]))
col4.metric("Total client position", gbp(result["total_client_position"]))

explain("Cash received now", "This is the cash left after the equity release is used to clear any remaining mortgage balance.")
explain("Amount due to Equity Lender", "This is the total amount payable to the equity lender at sale. If interest is not paid monthly, unpaid interest is added.")
explain("Remaining equity at sale", "This is the estimated amount left from the property after the equity lender has been repaid.")
explain("Total client position", "This combines remaining equity, cash received now, possible investment growth, and avoided mortgage payments.")

st.subheader("Decision Insight")
st.info(insight_message(result, years, property_growth_rate, interest_mode))

# ==========================================================
# THREE OPTION COMPARISON
# ==========================================================

st.subheader("Three Main Options")

option_comparison = pd.DataFrame({
    "Option": [
        "Take lifetime mortgage",
        "No equity release",
        "Sell property now"
    ],
    "Projected client outcome": [
        result["total_client_position"],
        result["no_equity_release_position"],
        result["future_value_sell_now_cash"]
    ]
})

st.dataframe(
    option_comparison.style.format({"Projected client outcome": "£{:,.0f}"}),
    use_container_width=True
)

fig_options, ax_options = plt.subplots()
ax_options.bar(option_comparison["Option"], option_comparison["Projected client outcome"])
ax_options.set_title("Projected Outcome: Three Main Options")
ax_options.set_ylabel("Projected client outcome (£)")
st.pyplot(fig_options)

explain(
    "Three main options",
    "This compares taking lifetime mortgage, keeping the property without equity release, or selling the property now and optionally investing the proceeds."
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
        "Cash received now",
        "Future property value",
        "Equity Lender share at disposal",
        "Rolled-up unpaid interest",
        "Amount due to Equity Lender",
        "Amount due after no-negative-equity cap",
        "Monthly equity release interest payment",
        "Total equity release interest paid",
        "Mortgage principal payments avoided",
        "Mortgage interest paid until sale",
        "Future value of cash balance",
        "Future value of mortgage payment savings",
        "Remaining equity at sale",
        "Total client position",
        "No-equity-release position",
        "Sell-now cash",
        "Sell-now future value",
        "Difference vs no equity release",
        "Difference vs sell now"
    ],
    "Value": [
        original_mortgage,
        result["remaining_mortgage"],
        result["client_ownership_value_now"],
        result["release_base"],
        result["equity_released"],
        result["net_cash_now"],
        result["future_property_value"],
        result["equity_lender_share_at_disposal"],
        result["rolled_up_interest"],
        result["amount_due_to_equity_lender"],
        result["amount_due_after_cap"],
        result["monthly_interest_payment"],
        result["total_interest_paid"],
        result["mortgage_principal_saved_until_sale"],
        result["mortgage_interest_paid_until_sale"],
        result["future_value_of_cash_balance"],
        result["future_value_of_mortgage_savings"],
        result["remaining_equity_at_sale"],
        result["total_client_position"],
        result["no_equity_release_position"],
        result["sell_now_cash"],
        result["future_value_sell_now_cash"],
        result["difference_vs_no_equity_release"],
        result["difference_vs_sell_now"],
    ]
})

st.dataframe(
    breakdown.style.format({"Value": "£{:,.0f}"}),
    use_container_width=True
)

# ==========================================================
# MULTIPLE FUTURES
# ==========================================================

st.subheader("Multiple Possible Futures")

growth_rates = sorted(set([-1.0, 0.0, 2.0, 3.0, 5.0, property_growth_rate]))

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
            mortgage_interest_rate,
            investment_return_rate,
            invest_cash_balance,
            invest_mortgage_savings,
            invest_sell_now_cash
        )

        scenario_rows.append({
            "Property growth": f"{growth:.1f}%",
            "Interest treatment": mode,
            "Future property value": scenario["future_property_value"],
            "Amount due to Equity Lender": scenario["amount_due_to_equity_lender"],
            "Remaining equity": scenario["remaining_equity_at_sale"],
            "Total client position": scenario["total_client_position"],
            "No equity release": scenario["no_equity_release_position"],
            "Sell now": scenario["future_value_sell_now_cash"],
        })

scenario_df = pd.DataFrame(scenario_rows)

st.dataframe(
    scenario_df.style.format({
        "Future property value": "£{:,.0f}",
        "Amount due to Equity Lender": "£{:,.0f}",
        "Remaining equity": "£{:,.0f}",
        "Total client position": "£{:,.0f}",
        "No equity release": "£{:,.0f}",
        "Sell now": "£{:,.0f}",
    }),
    use_container_width=True
)

# ==========================================================
# TIME IMPACT VIEW
# ==========================================================

st.subheader("Three-Option Comparison Over Time")

three_option_rows = []

for year in range(1, years + 1):
    year_result = calculate_model(
        original_mortgage,
        mortgage_paid_percent,
        current_property_value,
        equity_release_percent,
        annual_interest_rate,
        property_growth_rate,
        year,
        interest_mode,
        release_basis,
        mortgage_interest_rate,
        investment_return_rate,
        invest_cash_balance,
        invest_mortgage_savings,
        invest_sell_now_cash
    )

    three_option_rows.append({
        "Year": year,
        "Lifetime mortgage": year_result["total_client_position"],
        "No equity release": year_result["no_equity_release_position"],
        "Sell property now": year_result["future_value_sell_now_cash"],
    })

three_option_df = pd.DataFrame(three_option_rows)

fig_three, ax_three = plt.subplots()
ax_three.plot(three_option_df["Year"], three_option_df["Lifetime mortgage"], label="Lifetime mortgage")
ax_three.plot(three_option_df["Year"], three_option_df["No equity release"], label="No equity release")
ax_three.plot(three_option_df["Year"], three_option_df["Sell property now"], label="Sell property now")
ax_three.set_title("Comparison of All 3 Options Over Time")
ax_three.set_xlabel("Years")
ax_three.set_ylabel("Projected client outcome (£)")
ax_three.legend()
st.pyplot(fig_three)

st.dataframe(
    three_option_df.style.format({
        "Lifetime mortgage": "£{:,.0f}",
        "No equity release": "£{:,.0f}",
        "Sell property now": "£{:,.0f}",
    }),
    use_container_width=True
)

explain(
    "Three-option comparison over time",
    "This chart compares the projected outcome of taking lifetime mortgage, keeping the property without equity release, or selling the property now and optionally investing the proceeds."
)

# ==========================================================
# SCENARIO SAVING
# ==========================================================

st.subheader("Save Scenario")

scenario_name = st.text_input("Scenario name", value="Scenario 1")

if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []

if st.button("Save this scenario"):
    st.session_state.saved_scenarios.append({
        "Scenario": scenario_name,
        "Lifetime mortgage": result["total_client_position"],
        "No equity release": result["no_equity_release_position"],
        "Sell property now": result["future_value_sell_now_cash"],
        "Amount due to Equity Lender": result["amount_due_to_equity_lender"],
        "Remaining equity": result["remaining_equity_at_sale"],
    })
    st.success("Scenario saved.")

if st.session_state.saved_scenarios:
    saved_df = pd.DataFrame(st.session_state.saved_scenarios)

    st.dataframe(
        saved_df.style.format({
            "Lifetime mortgage": "£{:,.0f}",
            "No equity release": "£{:,.0f}",
            "Sell property now": "£{:,.0f}",
            "Amount due to Equity Lender": "£{:,.0f}",
            "Remaining equity": "£{:,.0f}",
        }),
        use_container_width=True
    )

# ==========================================================
# PDF EXPORT
# ==========================================================

st.subheader("Download Report")

report_inputs = {
    "Original mortgage / acquisition price": gbp(original_mortgage),
    "Mortgage already paid": f"{mortgage_paid_percent}%",
    "Current property value": gbp(current_property_value),
    "Equity release percentage": f"{equity_release_percent}%",
    "Equity release interest rate": f"{annual_interest_rate}%",
    "Existing mortgage interest rate": f"{mortgage_interest_rate}%",
    "Property growth assumption": f"{property_growth_rate}%",
    "Investment return assumption": f"{investment_return_rate}%",
    "Years until sale / care / death": years,
    "Interest treatment": interest_mode,
    "Release calculation basis": release_basis,
    "Invest remaining cash balance": invest_cash_balance,
    "Invest mortgage payment savings": invest_mortgage_savings,
    "Invest sell-now cash": invest_sell_now_cash,
}

pdf_report = create_pdf_report(result, report_inputs)

st.download_button(
    label="Download PDF report",
    data=pdf_report,
    file_name="lifetime_mortgage_decision_report.pdf",
    mime="application/pdf"
)

# ==========================================================
# FINAL SUMMARY
# ==========================================================

st.subheader("Plain-English Summary")

st.write(
    """
    This model compares three possible choices:

    1. **Take lifetime mortgage**  
       The client receives cash now, clears the remaining mortgage balance, may avoid future mortgage payments,
       and keeps any remaining property value after the Equity Lender is repaid.

    2. **No equity release**  
       The client keeps the property but continues to carry the existing mortgage until sale.

    3. **Sell property now**  
       The client receives the current property value after clearing the remaining mortgage, with an option to invest the proceeds.

    The model also considers:
    - property growth or decline,
    - interest paid monthly versus interest rolled up,
    - investment of released cash,
    - investment of avoided mortgage payments,
    - no negative equity protection,
    - and the opportunity benefit of not having to continue paying the existing mortgage.
    """
)
