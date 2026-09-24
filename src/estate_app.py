import streamlit as st
import pandas as pd

# --- 1. シミュレーション関数の定義 ---

def simulate_home_ownership_cost(
    property_price, down_payment, loan_term_years, interest_rate_annual, holding_years,
    estimated_sale_price, annual_maint_fee, annual_prop_tax, purchase_fee_rate,
    sale_fee_rate, building_ratio, building_depreciation_rate,
    is_new_home, annual_tax_paid
):
    loan_amount = property_price - down_payment
    monthly_rate = interest_rate_annual / 12
    total_months = loan_term_years * 12
    holding_months = holding_years * 12

    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**total_months) / ((1 + monthly_rate)**total_months - 1)
        remaining_balance = loan_amount * ((1 + monthly_rate)**total_months - (1 + monthly_rate)**holding_months) / ((1 + monthly_rate)**total_months - 1)
    else:
        monthly_payment = loan_amount / total_months
        remaining_balance = loan_amount - (monthly_payment * holding_months)
        
    remaining_balance = max(0, remaining_balance)
    total_loan_payment = monthly_payment * holding_months

    # 住宅ローン控除
    total_tax_deduction = 0
    deduction_years = 13 if is_new_home else 10
    deduction_rate = 0.007
    deduction_limit = 45000000 if is_new_home else 30000000
    
    for year in range(1, holding_years + 1):
        if year <= deduction_years:
            months_passed = year * 12
            if monthly_rate > 0:
                balance_at_yearend = loan_amount * ((1 + monthly_rate)**total_months - (1 + monthly_rate)**months_passed) / ((1 + monthly_rate)**total_months - 1)
            else:
                balance_at_yearend = loan_amount - (monthly_payment * months_passed)
            
            balance_at_yearend = max(0, balance_at_yearend)
            applicable_balance = min(balance_at_yearend, deduction_limit)
            calculated_deduction = applicable_balance * deduction_rate
            actual_deduction = min(calculated_deduction, annual_tax_paid)
            total_tax_deduction += actual_deduction

    initial_costs = property_price * purchase_fee_rate
    total_initial_outflow = down_payment + initial_costs
    total_maint_tax = (annual_maint_fee + annual_prop_tax) * holding_years

    # 譲渡所得税の計算
    sale_costs = estimated_sale_price * sale_fee_rate
    building_price = property_price * building_ratio
    total_depreciation = building_price * building_depreciation_rate * holding_years
    acquisition_cost = property_price + initial_costs - total_depreciation
    capital_gain = estimated_sale_price - sale_costs - acquisition_cost
    taxable_income = max(0, capital_gain - 30000000)
    tax_rate = 0.20315 if holding_years > 5 else 0.3963
    capital_gains_tax = taxable_income * tax_rate

    net_sale_proceeds = estimated_sale_price - sale_costs - remaining_balance - capital_gains_tax
    net_total_cost = (total_initial_outflow + total_loan_payment + total_maint_tax) - (total_tax_deduction + net_sale_proceeds)

    return {
        "net_total_cost": net_total_cost,
        "monthly_payment": monthly_payment
    }

def simulate_rent_cost(monthly_rent, holding_years, initial_fee_months, renewal_fee_months, annual_rent_increase_rate):
    initial_cost = monthly_rent * initial_fee_months
    num_renewals = (holding_years - 1) // 2 
    total_renewal_fees = monthly_rent * renewal_fee_months * num_renewals
    
    total_rent = 0
    current_rent = monthly_rent
    for year in range(holding_years):
        total_rent += current_rent * 12
        current_rent *= (1 + annual_rent_increase_rate)
        
    net_total_cost = initial_cost + total_rent + total_renewal_fees
    return {"net_total_cost": net_total_cost}

# --- 2. StreamlitのUI構築 ---

st.set_page_config(page_title="Buy vs Rent シミュレータ", layout="centered")
st.title("🏡 住宅購入 vs 賃貸 シミュレータ")

st.sidebar.header("📝 パラメータ設定")

# 購入の基本設定
st.sidebar.subheader("【1】住宅購入の基本")
is_new = st.sidebar.checkbox("新築マンション（チェックなしで中古）", value=False)
prop_price_man = st.sidebar.number_input("物件価格（万円）", min_value=1000, value=6000, step=100)
down_payment_man = st.sidebar.number_input("頭金（万円）", min_value=0, value=500, step=100)
loan_term_years = st.sidebar.number_input("ローン借入期間（年）", min_value=10, max_value=50, value=35)
interest_rate = st.sidebar.slider("ローン金利（年利％）", 0.1, 5.0, 1.0, 0.1) / 100

# 将来の売却設定
st.sidebar.subheader("【2】将来の売却想定")
sale_calc_method = st.sidebar.radio("売却価格の設定方法", ["年間下落率で指定", "具体的な売却価格を指定"])

if sale_calc_method == "年間下落率で指定":
    market_dep_rate = st.sidebar.slider("物件の年間下落率（％）", -2.0, 5.0, 1.5, 0.1) / 100
else:
    target_sale_price_man = st.sidebar.number_input("売却想定額（万円）", min_value=1000, value=5000, step=100)
    target_sale_price = target_sale_price_man * 10000
    st.sidebar.info("💡 売却年数によらず常にこの価格で売却できたと仮定してグラフを描画します")

# 賃貸の基本設定
st.sidebar.subheader("【3】賃貸の基本設定")
rent_man = st.sidebar.number_input("月額家賃（管理費込・万円）", min_value=5, value=18, step=1)

# 折りたたみ式の「詳細パラメータ」
with st.sidebar.expander("⚙️ 詳細パラメータ（維持費・税金・諸費用など）"):
    st.markdown("**◆ 購入：維持費と税金**")
    maint_fee_man = st.number_input("年間の管理費・修繕積立金（万円）", min_value=0, value=36, step=1)
    prop_tax_man = st.number_input("年間の固定資産税（万円）", min_value=0, value=12, step=1)
    annual_tax_paid_man = st.number_input("他で納入する税金（所得税など 万円）", min_value=0, value=50, step=1, help="住宅ローン控除の還付上限になります")
    
    st.markdown("**◆ 購入：不動産の諸費用・仕様**")
    purchase_fee_rate = st.slider("購入時諸費用率（%）", 1.0, 10.0, 7.0 if not is_new else 5.0, 0.1) / 100
    sale_fee_rate = st.slider("売却時諸費用率（%）", 1.0, 5.0, 3.5, 0.1) / 100
    building_ratio = st.slider("物件価格に占める建物割合（%）", 10, 100, 60, 1) / 100
    building_depreciation_rate = st.slider("建物の年間減価償却率（%）", 0.0, 5.0, 1.5, 0.1) / 100

    st.markdown("**◆ 賃貸：諸費用**")
    initial_fee_months = st.number_input("賃貸の初期費用（家賃何ヶ月分か）", min_value=0.0, value=4.0, step=0.5)
    renewal_fee_months = st.number_input("賃貸の更新料（2年ごと・家賃何ヶ月分か）", min_value=0.0, value=1.0, step=0.5)
    annual_rent_increase_rate = st.slider("年間の家賃上昇率（%）", 0.0, 5.0, 0.0, 0.1) / 100

# --- 3. グラフ描画と実行 ---

if st.button("📊 シミュレーションを実行する", type="primary", use_container_width=True):
    years = list(range(1, int(loan_term_years) + 1))
    buy_costs = []
    rent_costs = []
    
    property_price = prop_price_man * 10000
    down_payment = down_payment_man * 10000
    monthly_rent = rent_man * 10000
    annual_maint_fee = maint_fee_man * 10000
    annual_prop_tax = prop_tax_man * 10000
    annual_tax_paid = annual_tax_paid_man * 10000
    
    for y in years:
        if sale_calc_method == "年間下落率で指定":
            if is_new:
                sale_price = (property_price * 0.85) * ((1 - market_dep_rate) ** y)
            else:
                sale_price = property_price * ((1 - market_dep_rate) ** y)
        else:
            sale_price = target_sale_price

        buy_res = simulate_home_ownership_cost(
            property_price=property_price,
            down_payment=down_payment,
            loan_term_years=loan_term_years,
            interest_rate_annual=interest_rate,
            holding_years=y,
            estimated_sale_price=sale_price,
            annual_maint_fee=annual_maint_fee,
            annual_prop_tax=annual_prop_tax,
            purchase_fee_rate=purchase_fee_rate,
            sale_fee_rate=sale_fee_rate,
            building_ratio=building_ratio,
            building_depreciation_rate=building_depreciation_rate,
            is_new_home=is_new,
            annual_tax_paid=annual_tax_paid
        )
        
        rent_res = simulate_rent_cost(
            monthly_rent=monthly_rent,
            holding_years=y,
            initial_fee_months=initial_fee_months,
            renewal_fee_months=renewal_fee_months,
            annual_rent_increase_rate=annual_rent_increase_rate
        )
        
        buy_costs.append(buy_res["net_total_cost"] / 10000)
        rent_costs.append(rent_res["net_total_cost"] / 10000)

        monthly_mortgage = buy_res["monthly_payment"]

    # 月々の支払いイメージをダッシュボード表示
    st.markdown("💰 購入後の月々の支払いイメージ")
    col1, col2, col3 = st.columns(3)
    
    # 毎月のローン
    col1.metric("🏦 ローン返済額", f"{int(monthly_mortgage):,} 円")
    
    # 毎月の維持費（管理費・修繕積立金・固定資産税を12分割）
    monthly_maint_and_tax = (annual_maint_fee + annual_prop_tax) / 12
    col2.metric("🏢 管理費・税金等", f"{int(monthly_maint_and_tax):,} 円")
    
    # 上記の合計額
    total_monthly_outflow = monthly_mortgage + monthly_maint_and_tax
    col3.metric("合計キャッシュアウト", f"{int(total_monthly_outflow):,} 円", 
                delta=f"想定家賃より {int(total_monthly_outflow - monthly_rent):,}円", delta_color="inverse")

    # グラフ描画
    st.markdown("### 📈 持ち出し総額の推移（万円）")
    chart_data = pd.DataFrame({
        "購入（総持ち出し額）": buy_costs,
        "賃貸（総持ち出し額）": rent_costs
    }, index=years)
    
    st.line_chart(chart_data)
    
    # 損益分岐点の計算
    crossover = next((i + 1 for i in range(len(buy_costs)) if buy_costs[i] < rent_costs[i]), None)
    if crossover:
        st.success(f"💡 **{crossover}年目** に購入が賃貸のコストを下回ります")
    else:
        st.warning(f"💡 {int(loan_term_years)}年以内では賃貸の方が有利な計算になります")