"""
run_constrained_optimization.py
Authoritative Step 4 Optimization Pipeline:
Constrained Lifecycle Carbon vs. Compressive Strength Optimization & Pareto Frontier Analysis

Outputs generated:
- discrete_screening_results.csv
- continuous_optimization_results.csv
- summary_best_candidates_9cases.csv
- sensitivity_matrix_results.csv
- fig6_pareto_carbon_vs_strength.png
- fig7_sensitivity_analysis.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJ_DIR)

# -----------------------------------------------------------------------------
# 1. LOAD MASTER DATA AND RECONCILE MODELS
# -----------------------------------------------------------------------------
master_path = 'carbonation_master.csv'
if not os.path.exists(master_path):
    raise FileNotFoundError(f"Missing required master file: {master_path}")

df_master = pd.read_csv(master_path)

# Extract mix level parameters
mix_cols = [
    'mix_id', 'notation', 'wb_ratio', 'binder_content_kg_m3', 'sand_kg_m3', 'gravel_kg_m3',
    'air_content_pct', 'fc_28d_mpa', 'curing_days_USED', 'curing_time_days', 'scm1_type', 'scm1_pct',
    'scm2_type', 'scm2_pct', 'total_scm_pct', 'opc_kg_m3', 'water_kg_m3', 'scm_group',
    'fa_kg_m3', 'sg_kg_m3', 'ls_kg_m3', 'po_kg_m3', 'fa_pct', 'sg_pct', 'ls_pct', 'po_pct',
    'embodied_gwp_kgco2e_m3'
]
mixes = df_master[mix_cols].drop_duplicates('mix_id').reset_index(drop=True)
mixes.rename(columns={
    'wb_ratio': 'w_b',
    'binder_content_kg_m3': 'binder_kg_m3',
    'air_content_pct': 'air_pct',
    'fc_28d_mpa': 'fc_28d_MPa',
    'scm1_type': 'scm1_type_USED',
    'scm1_pct': 'scm1_pct_USED',
    'total_scm_pct': 'scm_total_pct',
    'opc_kg_m3': 'clinker_kg_m3',
    'curing_time_days': 'curing_days_dataset'
}, inplace=True)

# SCM Proportions: Reconcile C18 using official Mendeley dataset (C18 is 30% Slag, matching notation CmS-30SgF-0.6-250)
mixes['bw'] = 1.0 / mixes['w_b']
mixes['p_FaV'] = mixes['fa_pct'].astype(float)
mixes['p_SgF'] = mixes['sg_pct'].astype(float)
mixes['p_LS']  = mixes['ls_pct'].astype(float)
mixes['p_PoM'] = mixes['po_pct'].astype(float)

for t in ['FaV','SgF','LS','PoM']:
    mixes['q_'+t] = mixes['p_'+t] / 10.0

# Calculate natural carbonation rates k per mix
D = df_master.copy()
D['x'] = D['carbonation_depth_mm']
D['t'] = D['exposure_time_years']
D['condition'] = D['exposure_condition'].str.lower()

k_rows = []
for (m, c), g in D.groupby(['mix_id', 'condition']):
    k_val = (g.x * np.sqrt(g.t)).sum() / (g.t).sum()
    k_rows.append({'mix_id': m, 'condition': c, 'k': k_val})
df_k = pd.DataFrame(k_rows)
piv_k = df_k.pivot(index='mix_id', columns='condition', values='k').rename(columns={'sheltered':'k_sh', 'unsheltered':'k_un'}).reset_index()
mixes = mixes.merge(piv_k, on='mix_id')

mixes['lk_sh'] = np.log(mixes['k_sh'])
mixes['lk_un'] = np.log(mixes['k_un'])
mixes['d50_sh_mm'] = mixes['k_sh'] * np.sqrt(50.0)
mixes['d50_un_mm'] = mixes['k_un'] * np.sqrt(50.0)

# Calibrate Strength Model (without curing, matching validation report exactly)
m_fc = smf.ols('fc_28d_MPa ~ bw + air_pct + p_FaV + p_SgF + p_LS + p_PoM', data=mixes).fit()
cf_fc = m_fc.params.to_dict()

# Calibrate Carbonation Rate Models (without curing, R2 > 0.87)
m_ksh = smf.ols('lk_sh ~ q_FaV + q_SgF + q_LS + q_PoM + w_b', data=mixes).fit()
cf_ksh = m_ksh.params.to_dict()

m_kun = smf.ols('lk_un ~ q_FaV + q_SgF + q_LS + q_PoM + w_b', data=mixes).fit()
cf_kun = m_kun.params.to_dict()

# Calculate LOO-CV RMSE for strength model
h_diag = m_fc.get_influence().hat_matrix_diag
e_loo = m_fc.resid / (1.0 - h_diag)
loo_rmse_fc = np.sqrt(np.mean(e_loo**2))

# -----------------------------------------------------------------------------
# 2. DEFINITIONS: LCI EMISSION FACTORS & UPTAKE STOICHIOMETRY
# -----------------------------------------------------------------------------
def get_lci_factors(regime='economic'):
    if regime == 'cut_off':
        return {'opc': 0.840, 'fa': 0.005, 'sg': 0.020, 'ls': 0.025, 'po': 0.030, 'agg': 0.006, 'water': 0.0005, 'batch': 7.50}
    elif regime == 'mass':
        return {'opc': 0.840, 'fa': 0.030, 'sg': 0.120, 'ls': 0.025, 'po': 0.030, 'agg': 0.006, 'water': 0.0005, 'batch': 7.50}
    else: # economic (baseline)
        return {'opc': 0.840, 'fa': 0.015, 'sg': 0.060, 'ls': 0.025, 'po': 0.030, 'agg': 0.006, 'water': 0.0005, 'batch': 7.50}

def get_uptake_params(scenario='midpoint'):
    if scenario == 'low':
        return {
            'cao': {'opc': 0.62, 'sg': 0.36, 'fa': 0.02, 'ls': 0.00, 'po': 0.03},
            'alpha': {'opc': 0.60, 'sg': 0.45, 'fa': 0.35, 'ls': 0.00, 'po': 0.35}
        }
    elif scenario == 'high':
        return {
            'cao': {'opc': 0.67, 'sg': 0.44, 'fa': 0.08, 'ls': 0.00, 'po': 0.08},
            'alpha': {'opc': 0.80, 'sg': 0.70, 'fa': 0.55, 'ls': 0.00, 'po': 0.55}
        }
    else: # midpoint (baseline)
        return {
            'cao': {'opc': 0.65, 'sg': 0.40, 'fa': 0.05, 'ls': 0.00, 'po': 0.05},
            'alpha': {'opc': 0.70, 'sg': 0.60, 'fa': 0.50, 'ls': 0.00, 'po': 0.50}
        }

M_CO2_M_CaO = 44.01 / 56.08 # 0.78477
SV_SLAB = 5.0 # m2/m3 typical structural slab element

def predict_strength(wb, air_pct, p_fa, p_sg, p_ls, p_po):
    bw = 1.0 / wb
    return (cf_fc['Intercept'] + cf_fc['bw'] * bw + cf_fc['air_pct'] * air_pct
            + cf_fc['p_FaV'] * (p_fa * 100.0) + cf_fc['p_SgF'] * (p_sg * 100.0)
            + cf_fc['p_LS'] * (p_ls * 100.0) + cf_fc['p_PoM'] * (p_po * 100.0))

def predict_k(wb, p_fa, p_sg, p_ls, p_po, condition='sheltered'):
    cf = cf_ksh if condition == 'sheltered' else cf_kun
    lk = (cf['Intercept'] + cf['w_b'] * wb
          + cf['q_FaV'] * (p_fa * 10.0) + cf['q_SgF'] * (p_sg * 10.0)
          + cf['q_LS'] * (p_ls * 10.0) + cf['q_PoM'] * (p_po * 10.0))
    return np.exp(lk)

def evaluate_mix_lifecycle(wb, B, p_fa, p_sg, p_ls, p_po,
                            condition='sheltered',
                            lci_regime='economic',
                            uptake_scenario='midpoint',
                            kinetic_model='fickian',
                            power_exp=None):
    p_opc = max(0.0, 1.0 - (p_fa + p_sg + p_ls + p_po))
    m_opc = B * p_opc
    m_fa  = B * p_fa
    m_sg  = B * p_sg
    m_ls  = B * p_ls
    m_po  = B * p_po
    m_w   = B * wb
    
    # Volumetric aggregate balance: densities in kg/m3
    v_paste = (m_opc/3150.0 + m_fa/2300.0 + m_sg/2900.0 + m_ls/2700.0 + m_po/2500.0 + m_w/1000.0 + 0.02)
    v_agg = max(0.0, 1.0 - v_paste)
    m_agg = v_agg * 2650.0
    
    # Embodied GWP
    ef = get_lci_factors(lci_regime)
    gwp_emb = (m_opc * ef['opc'] + m_fa * ef['fa'] + m_sg * ef['sg'] + m_ls * ef['ls']
               + m_po * ef['po'] + m_agg * ef['agg'] + m_w * ef['water'] + ef['batch'])
    
    # Carbonation penetration depth at 50 years
    k_rate = predict_k(wb, p_fa, p_sg, p_ls, p_po, condition=condition)
    if kinetic_model == 'power':
        n_exp = power_exp if power_exp is not None else (0.509 if condition == 'sheltered' else 0.452)
        d50_mm = k_rate * (10.0**(0.5 - n_exp)) * (50.0**n_exp)
    else: # Fickian
        d50_mm = k_rate * np.sqrt(50.0)
        
    d50_m = d50_mm * 1e-3
    
    # Stoichiometric CO2 Uptake
    up_pars = get_uptake_params(uptake_scenario)
    cao_eff = (p_opc * up_pars['cao']['opc'] + p_sg * up_pars['cao']['sg'] +
               p_fa * up_pars['cao']['fa'] + p_ls * up_pars['cao']['ls'] +
               p_po * up_pars['cao']['po'])
    alpha_c = (p_opc * up_pars['alpha']['opc'] + p_sg * up_pars['alpha']['sg'] +
               p_fa * up_pars['alpha']['fa'] + p_ls * up_pars['alpha']['ls'] +
               p_po * up_pars['alpha']['po'])
    
    co2_cap = cao_eff * M_CO2_M_CaO * alpha_c
    uptake_m3 = d50_m * B * co2_cap * SV_SLAB
    gwp_net = gwp_emb - uptake_m3
    
    return {
        'gwp_embodied': gwp_emb,
        'co2_uptake': uptake_m3,
        'gwp_net': gwp_net,
        'd50_mm': d50_mm,
        'k_rate': k_rate,
        'm_opc': m_opc,
        'm_fa': m_fa,
        'm_sg': m_sg,
        'm_ls': m_ls,
        'm_agg': m_agg,
        'm_w': m_w
    }

TARGETS = [30.0, 35.0, 40.0]
COVERS  = [25.0, 30.0, 35.0]

def run_continuous_optimizer(target_fc, cover,
                             B_min=220.0, B_max=400.0,
                             max_fa=0.50, max_scm=0.50,
                             air_pct=2.0, margin=8.25,
                             condition='sheltered',
                             lci_regime='economic',
                             uptake_scenario='midpoint',
                             kinetic_model='fickian',
                             power_exp=None,
                             use_uncertainty_buffer=False,
                             durability_factor=None,
                             max_wb_override=None,
                             pce_dosage=0.0,
                             ef_pce=1.69):
    required_fc = target_fc + margin
    if durability_factor is None:
        durability_factor = 1.15 if use_uncertainty_buffer else 1.0
    if max_wb_override is not None:
        max_wb = max_wb_override
    else:
        max_wb = 0.55 if condition == 'sheltered' else 0.50
    
    def objective(x):
        wb, B, p_fa, p_sg, p_ls, p_po = x
        res = evaluate_mix_lifecycle(wb, B, p_fa, p_sg, p_ls, p_po,
                                     condition=condition,
                                     lci_regime=lci_regime,
                                     uptake_scenario=uptake_scenario,
                                     kinetic_model=kinetic_model,
                                     power_exp=power_exp)
        pce_penalty = (pce_dosage * B * ef_pce) if pce_dosage > 0.0 else 0.0
        return res['gwp_net'] + pce_penalty
    
    bounds = [
        (0.45, max_wb),
        (B_min, B_max),
        (0.0, min(max_fa, max_scm)),
        (0.0, max_scm),
        (0.0, 0.30),
        (0.0, 0.30)
    ]
    
    def constr_scm_tot(x):
        return max_scm - (x[2] + x[3] + x[4] + x[5])
    
    def constr_strength(x):
        return predict_strength(x[0], air_pct, x[2], x[3], x[4], x[5]) - required_fc
    
    def constr_durability(x):
        res = evaluate_mix_lifecycle(x[0], x[1], x[2], x[3], x[4], x[5],
                                     condition=condition,
                                     kinetic_model=kinetic_model,
                                     power_exp=power_exp)
        return cover - (res['d50_mm'] * durability_factor)
    
    constraints = [
        {'type': 'ineq', 'fun': constr_scm_tot},
        {'type': 'ineq', 'fun': constr_strength},
        {'type': 'ineq', 'fun': constr_durability}
    ]
    
    starts = [
        [min(0.50, max_wb), 300.0, 0.00, 0.00, 0.00, 0.00],
        [min(0.50, max_wb), 320.0, 0.20, 0.00, 0.00, 0.00],
        [min(0.50, max_wb), 320.0, 0.00, 0.30, 0.00, 0.00],
        [0.45, 350.0, 0.00, 0.50, 0.00, 0.00],
        [0.48, 330.0, 0.15, 0.15, 0.00, 0.00],
        [0.55, 280.0, 0.00, 0.20, 0.10, 0.00],
        [0.60, 250.0, 0.00, 0.00, 0.00, 0.00],
        [0.45, 380.0, 0.30, 0.00, 0.00, 0.00],
        [0.52, 310.0, 0.00, 0.40, 0.00, 0.00],
        [0.50, 300.0, 0.10, 0.20, 0.00, 0.00],
        [0.45, B_min, 0.25, 0.25, 0.00, 0.00],
        [0.45, B_min, 0.10, 0.40, 0.00, 0.00]
    ]
    
    best_res, best_val = None, 1e9
    
    for s in starts:
        s_clamped = [np.clip(s[i], bounds[i][0], bounds[i][1]) for i in range(6)]
        try:
            res = minimize(objective, s_clamped, method='SLSQP', bounds=bounds,
                           constraints=constraints, options={'maxiter': 600, 'ftol': 1e-7})
            if res.success and res.fun < best_val:
                fc_val = predict_strength(res.x[0], air_pct, res.x[2], res.x[3], res.x[4], res.x[5])
                d_val  = evaluate_mix_lifecycle(res.x[0], res.x[1], res.x[2], res.x[3], res.x[4], res.x[5],
                                                condition=condition, kinetic_model=kinetic_model, power_exp=power_exp)['d50_mm']
                scm_sum = sum(res.x[2:])
                if (fc_val >= required_fc - 0.05) and (d_val * durability_factor <= cover + 0.05) and (scm_sum <= max_scm + 0.001):
                    best_val = res.fun
                    best_res = res
        except Exception:
            continue
            
    if best_res is not None:
        x_opt = best_res.x
        eval_dict = evaluate_mix_lifecycle(x_opt[0], x_opt[1], x_opt[2], x_opt[3], x_opt[4], x_opt[5],
                                           condition=condition, lci_regime=lci_regime,
                                           uptake_scenario=uptake_scenario,
                                           kinetic_model=kinetic_model, power_exp=power_exp)
        pred_fc = predict_strength(x_opt[0], air_pct, x_opt[2], x_opt[3], x_opt[4], x_opt[5])
        pce_val = (pce_dosage * x_opt[1] * ef_pce) if pce_dosage > 0.0 else 0.0
        return {
            'status': 'FEASIBLE',
            'w_b': x_opt[0],
            'binder_kg_m3': x_opt[1],
            'p_fa_pct': x_opt[2] * 100.0,
            'p_sg_pct': x_opt[3] * 100.0,
            'p_ls_pct': x_opt[4] * 100.0,
            'p_po_pct': x_opt[5] * 100.0,
            'p_opc_pct': (1.0 - sum(x_opt[2:])) * 100.0,
            'pred_fc_MPa': pred_fc,
            'd50_mm': eval_dict['d50_mm'],
            'k_rate': eval_dict['k_rate'],
            'gwp_embodied': eval_dict['gwp_embodied'] + pce_val,
            'co2_uptake': eval_dict['co2_uptake'],
            'gwp_net': eval_dict['gwp_net'] + pce_val,
            'pce_gwp': pce_val,
            'm_opc_kg': eval_dict['m_opc'],
            'm_fa_kg': eval_dict['m_fa'],
            'm_sg_kg': eval_dict['m_sg'],
            'm_ls_kg': eval_dict['m_ls'],
            'm_agg_kg': eval_dict['m_agg'],
            'm_w_kg': eval_dict['m_w']
        }
    else:
        return {'status': 'INFEASIBLE'}

def main():
    print("="*80)
    print("STEP 4: CONSTRAINED LIFECYCLE CARBON OPTIMIZATION & PARETO FRONTIER ANALYSIS")
    print("="*80)
    print(f"Loaded master dataset: {df_master.shape[0]} observations, {df_master['mix_id'].nunique()} unique mixes.")
    print(f"Reconciled Strength Model: R2={m_fc.rsquared:.3f}, LOO-RMSE={loo_rmse_fc:.3f} MPa (codified margin = 8.25 MPa per IS 10262 Table 2)")
    print(f"Reconciled Sheltered k Model: Adj R2={m_ksh.rsquared_adj:.3f}")
    print(f"Reconciled Unsheltered k Model: Adj R2={m_kun.rsquared_adj:.3f}")

    # -----------------------------------------------------------------------------
    # 3. DISCRETE MIX SCREENING: SHELTERED & UNSHELTERED (NOMINAL & UNCERTAINTY)
    # -----------------------------------------------------------------------------
    print("\n" + "="*80)
    print("PART A: DISCRETE SCREENING OF 45 PHYSICAL MIXES")
    print("="*80)

    discrete_records = []

    for _, r in mixes.iterrows():
        mix_id = r['mix_id']
        notation = r['notation']
        fc_meas = r['fc_28d_MPa']
        d50_sh = r['d50_sh_mm']
        d50_un = r['d50_un_mm']
        gwp_emb = r['embodied_gwp_kgco2e_m3']
        
        # Calculate uptake for measured mix
        res_sh = evaluate_mix_lifecycle(r['w_b'], r['binder_kg_m3'],
                                        r['p_FaV']/100.0, r['p_SgF']/100.0, r['p_LS']/100.0, r['p_PoM']/100.0,
                                        condition='sheltered')
        res_un = evaluate_mix_lifecycle(r['w_b'], r['binder_kg_m3'],
                                        r['p_FaV']/100.0, r['p_SgF']/100.0, r['p_LS']/100.0, r['p_PoM']/100.0,
                                        condition='unsheltered')
        
        for target in TARGETS:
            for cover in COVERS:
                # Sheltered: Nominal vs +15% Uncertainty Buffer vs IS 10262 Design Margins
                pass_sh_nom = (fc_meas >= target) and (d50_sh <= cover)
                pass_sh_unc = (fc_meas >= target) and (d50_sh * 1.15 <= cover)
                pass_sh_buf_nom = (fc_meas >= target + 4.4) and (d50_sh <= cover)
                pass_sh_buf_unc = (fc_meas >= target + 4.4) and (d50_sh * 1.15 <= cover)
                pass_sh_is4_nom = (fc_meas >= target + 6.6) and (d50_sh <= cover)
                pass_sh_is4_unc = (fc_meas >= target + 6.6) and (d50_sh * 1.15 <= cover)
                pass_sh_is5_nom = (fc_meas >= target + 8.25) and (d50_sh <= cover)
                pass_sh_is5_unc = (fc_meas >= target + 8.25) and (d50_sh * 1.15 <= cover)
                
                reasons_sh_nom = []
                if fc_meas < target:
                    reasons_sh_nom.append(f"Strength deficient ({fc_meas:.1f} < {target:.1f} MPa)")
                if d50_sh > cover:
                    reasons_sh_nom.append(f"Cover breached ({d50_sh:.1f} > {cover:.0f} mm)")
                reason_str_sh_nom = "; ".join(reasons_sh_nom) if reasons_sh_nom else "FEASIBLE"
                
                # Unsheltered: Nominal vs +15% Uncertainty Buffer vs IS 10262 Design Margins
                pass_un_nom = (fc_meas >= target) and (d50_un <= cover)
                pass_un_unc = (fc_meas >= target) and (d50_un * 1.15 <= cover)
                pass_un_buf_nom = (fc_meas >= target + 4.4) and (d50_un <= cover)
                pass_un_buf_unc = (fc_meas >= target + 4.4) and (d50_un * 1.15 <= cover)
                pass_un_is4_nom = (fc_meas >= target + 6.6) and (d50_un <= cover)
                pass_un_is4_unc = (fc_meas >= target + 6.6) and (d50_un * 1.15 <= cover)
                pass_un_is5_nom = (fc_meas >= target + 8.25) and (d50_un <= cover)
                pass_un_is5_unc = (fc_meas >= target + 8.25) and (d50_un * 1.15 <= cover)
                
                reasons_un_nom = []
                if fc_meas < target:
                    reasons_un_nom.append(f"Strength deficient ({fc_meas:.1f} < {target:.1f} MPa)")
                if d50_un > cover:
                    reasons_un_nom.append(f"Cover breached ({d50_un:.1f} > {cover:.0f} mm)")
                reason_str_un_nom = "; ".join(reasons_un_nom) if reasons_un_nom else "FEASIBLE"
                
                discrete_records.append({
                    'mix_id': mix_id,
                    'notation': notation,
                    'scm_group': r['scm_group'],
                    'w_b': r['w_b'],
                    'binder_kg_m3': r['binder_kg_m3'],
                    'fc_28d_meas_MPa': fc_meas,
                    'target_fc_MPa': target,
                    'heuristic_margin_MPa': 4.4,
                    'required_fc_MPa': target,
                    'buffered_fc_MPa': target + 4.4,
                    'is10262_s4_fc_MPa': target + 6.6,
                    'is10262_s5_fc_MPa': target + 8.25,
                    'cover_mm': cover,
                    'd50_sh_mm': d50_sh,
                    'd50_sh_buffered_mm': d50_sh * 1.15,
                    'd50_un_mm': d50_un,
                    'd50_un_buffered_mm': d50_un * 1.15,
                    'gwp_embodied': gwp_emb,
                    'net_gwp_sh': res_sh['gwp_net'],
                    'uptake_sh': res_sh['co2_uptake'],
                    'net_gwp_un': res_un['gwp_net'],
                    'uptake_un': res_un['co2_uptake'],
                    'feasible_sh_nominal': pass_sh_nom,
                    'feasible_sh_unc15': pass_sh_unc,
                    'feasible_sh_buf_nominal': pass_sh_buf_nom,
                    'feasible_sh_buf_unc15': pass_sh_buf_unc,
                    'feasible_sh_is4_nominal': pass_sh_is4_nom,
                    'feasible_sh_is4_unc15': pass_sh_is4_unc,
                    'feasible_sh_is5_nominal': pass_sh_is5_nom,
                    'feasible_sh_is5_unc15': pass_sh_is5_unc,
                    'reason_sh_nominal': reason_str_sh_nom,
                    'feasible_un_nominal': pass_un_nom,
                    'feasible_un_unc15': pass_un_unc,
                    'feasible_un_buf_nominal': pass_un_buf_nom,
                    'feasible_un_buf_unc15': pass_un_buf_unc,
                    'feasible_un_is4_nominal': pass_un_is4_nom,
                    'feasible_un_is4_unc15': pass_un_is4_unc,
                    'feasible_un_is5_nominal': pass_un_is5_nom,
                    'feasible_un_is5_unc15': pass_un_is5_unc,
                    'reason_un_nominal': reason_str_un_nom
                })

    df_discrete_results = pd.DataFrame(discrete_records)
    df_discrete_results.to_csv('discrete_screening_results.csv', index=False)
    print("Saved complete discrete screening results to: discrete_screening_results.csv")

    # -----------------------------------------------------------------------------
    # 4. CONTINUOUS CONSTRAINED OPTIMIZATION VIA SLSQP (MULTI-START)
    # -----------------------------------------------------------------------------
    print("\n" + "="*80)
    print("PART B: CONTINUOUS CONSTRAINED OPTIMIZATION VIA SLSQP (MULTI-START)")
    print("="*80)

    # Run continuous grid for empirical and structural envelopes under both Nominal and Uncertainty
    cont_results = []
    for cond in ['sheltered', 'unsheltered']:
        for unc_flag, unc_name in [(False, 'Nominal'), (True, 'Uncertainty_15')]:
            env_tuples = [(220.0, 'Empirical (B>=220)')]
            if cond == 'sheltered':
                env_tuples.append((280.0, 'Structural (B>=280)'))
                env_tuples.append((300.0, 'IS456_Mild (B>=300)'))
            else:
                env_tuples.append((280.0, 'Structural (B>=280)'))
                env_tuples.append((300.0, 'Structural (B>=300)'))
                env_tuples.append((320.0, 'IS456_Severe (B>=320)'))

            for B_min_val, env_name in env_tuples:
                for target in TARGETS:
                    for cover in COVERS:
                        max_fa_val = 0.35
                        wb_override = 0.45 if 'Severe' in env_name else None
                        res_opt = run_continuous_optimizer(target, cover, B_min=B_min_val, condition=cond, max_fa=max_fa_val, use_uncertainty_buffer=unc_flag, margin=8.25, max_wb_override=wb_override)
                        row = {
                            'condition': cond,
                            'envelope': env_name,
                            'durability_mode': unc_name,
                            'use_uncertainty_buffer': unc_flag,
                            'target_fc_MPa': target,
                            'cover_mm': cover,
                            'air_pct': 2.0,
                            'margin_MPa': 8.25,
                            'status': res_opt['status']
                        }
                        if res_opt['status'] == 'FEASIBLE':
                            row.update(res_opt)
                        cont_results.append(row)

    df_cont_results = pd.DataFrame(cont_results)
    df_cont_results.to_csv('continuous_optimization_results.csv', index=False)
    print("Saved continuous optimization results to: continuous_optimization_results.csv")

    # -----------------------------------------------------------------------------
    # 5. SUMMARY OF BEST CANDIDATES FOR ALL 9 CASES (SHELTERED & UNSHELTERED)
    # -----------------------------------------------------------------------------
    print("\n" + "="*80)
    print("PART C: AUTHORITATIVE SUMMARY OF BEST CANDIDATES ACROSS 9 CASES")
    print("="*80)

    grade_map = {30.0: 'C30/37', 35.0: 'C35/45', 40.0: 'C40/50'}
    summary_9cases = []
    for cond in ['sheltered', 'unsheltered']:
        struct_env_name = 'Structural (B>=280)' if cond == 'sheltered' else 'Structural (B>=300)'
        wb_max_env = 0.55 if cond == 'sheltered' else 0.50
        denom_env = 35 if cond == 'sheltered' else 26
        c_code = 'sh' if cond == 'sheltered' else 'un'

        for target in TARGETS:
            for cover in COVERS:
                # Discrete: Nominal screen (fc_meas >= target, d50 <= cover, w_b <= wb_max_env)
                sub_d_nom = df_discrete_results[
                    (df_discrete_results['target_fc_MPa'] == target) &
                    (df_discrete_results['cover_mm'] == cover) &
                    (df_discrete_results['w_b'] <= wb_max_env) &
                    (df_discrete_results[f'feasible_{c_code}_nominal'] == True)
                ]
                cnt_nom = len(sub_d_nom)
                if not sub_d_nom.empty:
                    best_d_nom = sub_d_nom.sort_values(f'net_gwp_{c_code}').iloc[0]
                    d_id_nom = best_d_nom['mix_id']
                    d_not_nom = best_d_nom['notation']
                    d_fc_nom = best_d_nom['fc_28d_meas_MPa']
                    d_d50_nom = best_d_nom[f'd50_{c_code}_mm']
                    d_net_nom = best_d_nom[f'net_gwp_{c_code}']
                else:
                    d_id_nom, d_not_nom, d_fc_nom, d_d50_nom, d_net_nom = 'NONE', 'None feasible', np.nan, np.nan, np.nan

                # Discrete: +15% Uncertainty buffer (fc_meas >= target, 1.15*d50 <= cover, w_b <= wb_max_env)
                sub_d_unc = df_discrete_results[
                    (df_discrete_results['target_fc_MPa'] == target) &
                    (df_discrete_results['cover_mm'] == cover) &
                    (df_discrete_results['w_b'] <= wb_max_env) &
                    (df_discrete_results[f'feasible_{c_code}_unc15'] == True)
                ]
                cnt_unc = len(sub_d_unc)
                if not sub_d_unc.empty:
                    best_d_unc = sub_d_unc.sort_values(f'net_gwp_{c_code}').iloc[0]
                    d_id_unc = best_d_unc['mix_id']
                    d_not_unc = best_d_unc['notation']
                    d_fc_unc = best_d_unc['fc_28d_meas_MPa']
                    d_d50_unc = best_d_unc[f'd50_{c_code}_mm']
                    d_net_unc = best_d_unc[f'net_gwp_{c_code}']
                else:
                    d_id_unc, d_not_unc, d_fc_unc, d_d50_unc, d_net_unc = 'NONE', 'None feasible', np.nan, np.nan, np.nan

                # Discrete: IS 10262 Margin s=4 (+6.6 MPa) under Nominal Durability
                sub_d_is4_nom = df_discrete_results[
                    (df_discrete_results['target_fc_MPa'] == target) &
                    (df_discrete_results['cover_mm'] == cover) &
                    (df_discrete_results['w_b'] <= wb_max_env) &
                    (df_discrete_results[f'feasible_{c_code}_is4_nominal'] == True)
                ]
                cnt_is4_nom = len(sub_d_is4_nom)
                if not sub_d_is4_nom.empty:
                    best_d_is4_nom = sub_d_is4_nom.sort_values(f'net_gwp_{c_code}').iloc[0]
                    d_id_is4_nom, d_net_is4_nom = best_d_is4_nom['mix_id'], best_d_is4_nom[f'net_gwp_{c_code}']
                else:
                    d_id_is4_nom, d_net_is4_nom = 'NONE', np.nan

                # Discrete: IS 10262 Margin s=4 (+6.6 MPa) under +15% Uncertainty Durability
                sub_d_is4_unc = df_discrete_results[
                    (df_discrete_results['target_fc_MPa'] == target) &
                    (df_discrete_results['cover_mm'] == cover) &
                    (df_discrete_results['w_b'] <= wb_max_env) &
                    (df_discrete_results[f'feasible_{c_code}_is4_unc15'] == True)
                ]
                cnt_is4_unc = len(sub_d_is4_unc)
                if not sub_d_is4_unc.empty:
                    best_d_is4_unc = sub_d_is4_unc.sort_values(f'net_gwp_{c_code}').iloc[0]
                    d_id_is4_unc, d_net_is4_unc = best_d_is4_unc['mix_id'], best_d_is4_unc[f'net_gwp_{c_code}']
                else:
                    d_id_is4_unc, d_net_is4_unc = 'NONE', np.nan

                # Discrete: IS 10262 Margin s=5 (+8.25 MPa) under Nominal Durability
                sub_d_is5_nom = df_discrete_results[
                    (df_discrete_results['target_fc_MPa'] == target) &
                    (df_discrete_results['cover_mm'] == cover) &
                    (df_discrete_results['w_b'] <= wb_max_env) &
                    (df_discrete_results[f'feasible_{c_code}_is5_nominal'] == True)
                ]
                cnt_is5_nom = len(sub_d_is5_nom)
                if not sub_d_is5_nom.empty:
                    best_d_is5_nom = sub_d_is5_nom.sort_values(f'net_gwp_{c_code}').iloc[0]
                    d_id_is5_nom, d_net_is5_nom = best_d_is5_nom['mix_id'], best_d_is5_nom[f'net_gwp_{c_code}']
                else:
                    d_id_is5_nom, d_net_is5_nom = 'NONE', np.nan

                # Discrete: IS 10262 Margin s=5 (+8.25 MPa) under +15% Uncertainty Durability
                sub_d_is5_unc = df_discrete_results[
                    (df_discrete_results['target_fc_MPa'] == target) &
                    (df_discrete_results['cover_mm'] == cover) &
                    (df_discrete_results['w_b'] <= wb_max_env) &
                    (df_discrete_results[f'feasible_{c_code}_is5_unc15'] == True)
                ]
                cnt_is5_unc = len(sub_d_is5_unc)
                if not sub_d_is5_unc.empty:
                    best_d_is5_unc = sub_d_is5_unc.sort_values(f'net_gwp_{c_code}').iloc[0]
                    d_id_is5_unc, d_net_is5_unc = best_d_is5_unc['mix_id'], best_d_is5_unc[f'net_gwp_{c_code}']
                else:
                    d_id_is5_unc, d_net_is5_unc = 'NONE', np.nan

                # Discrete: Buffered screen (IS 10262 Table 2 s=5.0 [+8.25 MPa] & +15% kinetic buffer, w_b <= wb_max_env)
                d_id_buf = d_id_is5_unc
                d_not_buf = best_d_is5_unc['notation'] if not sub_d_is5_unc.empty else 'None feasible'
                d_fc_buf = best_d_is5_unc['fc_28d_meas_MPa'] if not sub_d_is5_unc.empty else np.nan
                d_d50_buf = best_d_is5_unc[f'd50_{c_code}_mm'] if not sub_d_is5_unc.empty else np.nan
                d_net_buf = best_d_is5_unc[f'net_gwp_{c_code}'] if not sub_d_is5_unc.empty else np.nan
                cnt_buf = cnt_is5_unc

                # Continuous: Structural Envelope Nominal (d50 <= cover)
                sub_c_nom = df_cont_results[
                    (df_cont_results['condition'] == cond) &
                    (df_cont_results['envelope'] == struct_env_name) &
                    (df_cont_results['durability_mode'] == 'Nominal') &
                    (df_cont_results['target_fc_MPa'] == target) &
                    (df_cont_results['cover_mm'] == cover)
                ]
                if not sub_c_nom.empty and sub_c_nom.iloc[0]['status'] == 'FEASIBLE':
                    c_nom = sub_c_nom.iloc[0]
                    parts_nom = [f"wb={c_nom['w_b']:.2f}", f"FA={c_nom['p_fa_pct']:.1f}%", f"SG={c_nom['p_sg_pct']:.1f}%"]
                    if c_nom['p_ls_pct'] > 0.05:
                        parts_nom.append(f"LS={c_nom['p_ls_pct']:.1f}%")
                    if c_nom['p_po_pct'] > 0.05:
                        parts_nom.append(f"PO={c_nom['p_po_pct']:.1f}%")
                    c_nom_comp = ", ".join(parts_nom)
                    c_nom_fc = c_nom['pred_fc_MPa']
                    c_nom_d50 = c_nom['d50_mm']
                    c_nom_net = c_nom['gwp_net']
                else:
                    c_nom_comp, c_nom_fc, c_nom_d50, c_nom_net = 'INFEASIBLE', np.nan, np.nan, np.nan

                # Continuous: Structural Envelope +15% Uncertainty (1.15*d50 <= cover)
                sub_c_unc = df_cont_results[
                    (df_cont_results['condition'] == cond) &
                    (df_cont_results['envelope'] == struct_env_name) &
                    (df_cont_results['durability_mode'] == 'Uncertainty_15') &
                    (df_cont_results['target_fc_MPa'] == target) &
                    (df_cont_results['cover_mm'] == cover)
                ]
                if not sub_c_unc.empty and sub_c_unc.iloc[0]['status'] == 'FEASIBLE':
                    c_unc = sub_c_unc.iloc[0]
                    parts_unc = [f"wb={c_unc['w_b']:.2f}", f"FA={c_unc['p_fa_pct']:.1f}%", f"SG={c_unc['p_sg_pct']:.1f}%"]
                    if c_unc['p_ls_pct'] > 0.05:
                        parts_unc.append(f"LS={c_unc['p_ls_pct']:.1f}%")
                    if c_unc['p_po_pct'] > 0.05:
                        parts_unc.append(f"PO={c_unc['p_po_pct']:.1f}%")
                    c_unc_comp = ", ".join(parts_unc)
                    c_unc_fc = c_unc['pred_fc_MPa']
                    c_unc_d50 = c_unc['d50_mm']
                    c_unc_net = c_unc['gwp_net']
                else:
                    c_unc_comp, c_unc_fc, c_unc_d50, c_unc_net = 'INFEASIBLE', np.nan, np.nan, np.nan

                summary_9cases.append({
                    'Exposure_Condition': cond.capitalize(),
                    'Target_Grade': grade_map[target],
                    'Target_fc_Demand_MPa': target,
                    'Cover_mm': int(cover),
                    'Discrete_Feasible_Count_Nominal': f"{cnt_nom}/{denom_env}",
                    'Discrete_Feasible_Count_Unc15': f"{cnt_unc}/{denom_env}",
                    'Discrete_Feasible_Count_IS4_Nominal': f"{cnt_is4_nom}/{denom_env}",
                    'Discrete_Feasible_Count_IS4_Unc15': f"{cnt_is4_unc}/{denom_env}",
                    'Discrete_Feasible_Count_IS5_Nominal': f"{cnt_is5_nom}/{denom_env}",
                    'Discrete_Feasible_Count_IS5_Unc15': f"{cnt_is5_unc}/{denom_env}",
                    'Discrete_Feasible_Count_Buffered': f"{cnt_buf}/{denom_env}",
                    'Discrete_Nominal_Best_Mix': d_id_nom,
                    'Discrete_Nominal_Notation': d_not_nom,
                    'Discrete_Nominal_fc_MPa': round(d_fc_nom, 1) if not np.isnan(d_fc_nom) else np.nan,
                    'Discrete_Nominal_d50_mm': round(d_d50_nom, 1) if not np.isnan(d_d50_nom) else np.nan,
                    'Discrete_Nominal_Net_GWP': round(d_net_nom, 1) if not np.isnan(d_net_nom) else np.nan,
                    'Discrete_IS4_Nominal_Best_Mix': d_id_is4_nom,
                    'Discrete_IS4_Nominal_Net_GWP': round(d_net_is4_nom, 1) if not np.isnan(d_net_is4_nom) else np.nan,
                    'Discrete_IS4_Unc15_Best_Mix': d_id_is4_unc,
                    'Discrete_IS4_Unc15_Net_GWP': round(d_net_is4_unc, 1) if not np.isnan(d_net_is4_unc) else np.nan,
                    'Discrete_IS5_Nominal_Best_Mix': d_id_is5_nom,
                    'Discrete_IS5_Nominal_Net_GWP': round(d_net_is5_nom, 1) if not np.isnan(d_net_is5_nom) else np.nan,
                    'Discrete_IS5_Unc15_Best_Mix': d_id_is5_unc,
                    'Discrete_IS5_Unc15_Net_GWP': round(d_net_is5_unc, 1) if not np.isnan(d_net_is5_unc) else np.nan,
                    'Discrete_Unc15_Best_Mix': d_id_unc,
                    'Discrete_Unc15_Notation': d_not_unc,
                    'Discrete_Unc15_fc_MPa': round(d_fc_unc, 1) if not np.isnan(d_fc_unc) else np.nan,
                    'Discrete_Unc15_d50_mm': round(d_d50_unc, 1) if not np.isnan(d_d50_unc) else np.nan,
                    'Discrete_Unc15_Net_GWP': round(d_net_unc, 1) if not np.isnan(d_net_unc) else np.nan,
                    'Discrete_Buffered_Best_Mix': d_id_buf,
                    'Discrete_Buffered_Notation': d_not_buf,
                    'Discrete_Buffered_fc_MPa': round(d_fc_buf, 1) if not np.isnan(d_fc_buf) else np.nan,
                    'Discrete_Buffered_d50_mm': round(d_d50_buf, 1) if not np.isnan(d_d50_buf) else np.nan,
                    'Discrete_Buffered_Net_GWP': round(d_net_buf, 1) if not np.isnan(d_net_buf) else np.nan,
                    'Continuous_Nominal_Mix': c_nom_comp,
                    'Continuous_Nominal_fc_MPa': round(c_nom_fc, 1) if not np.isnan(c_nom_fc) else np.nan,
                    'Continuous_Nominal_d50_mm': round(c_nom_d50, 1) if not np.isnan(c_nom_d50) else np.nan,
                    'Continuous_Nominal_Net_GWP': round(c_nom_net, 1) if not np.isnan(c_nom_net) else np.nan,
                    'Continuous_Unc15_Mix': c_unc_comp,
                    'Continuous_Unc15_fc_MPa': round(c_unc_fc, 1) if not np.isnan(c_unc_fc) else np.nan,
                    'Continuous_Unc15_d50_mm': round(c_unc_d50, 1) if not np.isnan(c_unc_d50) else np.nan,
                    'Continuous_Unc15_Net_GWP': round(c_unc_net, 1) if not np.isnan(c_unc_net) else np.nan
                })

    df_summary_9cases = pd.DataFrame(summary_9cases)
    df_summary_9cases.to_csv('summary_best_candidates_9cases.csv', index=False)
    print("Saved 9-case summary to: summary_best_candidates_9cases.csv")
    print(df_summary_9cases[['Exposure_Condition', 'Target_Grade', 'Cover_mm', 'Discrete_Feasible_Count_Nominal', 'Discrete_Nominal_Best_Mix', 'Discrete_Feasible_Count_Buffered', 'Discrete_Buffered_Best_Mix', 'Continuous_Nominal_Net_GWP', 'Continuous_Unc15_Net_GWP']].to_string(index=False))

    # -----------------------------------------------------------------------------
    # 6. SENSITIVITY & ROBUSTNESS ANALYSIS (AT STRUCTURAL BASELINE B = 280 kg/m3)
    # -----------------------------------------------------------------------------
    print("\n" + "="*80)
    print("PART D: SENSITIVITY & ROBUSTNESS SWEEPS (STRUCTURAL BASELINE B = 280 kg/m3)")
    print("="*80)

    sens_records = []
    BASE_TARGET = 35.0
    BASE_COVER  = 30.0
    BASE_B_STRUCT = 280.0

    # 1. Microclimate Exposure: Sheltered vs Unsheltered
    for cond in ['sheltered', 'unsheltered']:
        b_val = BASE_B_STRUCT if cond == 'sheltered' else 300.0
        max_fa_val = 0.35
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=b_val, condition=cond, max_fa=max_fa_val)
        sens_records.append({
            'sweep_dimension': 'Exposure Microclimate',
            'scenario': cond.capitalize(),
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 2. SCM Allocation Regime: Economic vs Cut-off vs Mass
    for alloc in ['economic', 'cut_off', 'mass']:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, lci_regime=alloc)
        sens_records.append({
            'sweep_dimension': 'SCM Allocation Regime',
            'scenario': alloc.capitalize(),
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 3. Kinetics: Fickian (n=0.50) vs Empirical Power-Law (n=0.509 sheltered, n=0.452 unsheltered)
    for kin, n_val in [('Fickian (n=0.50)', 0.50), ('Power-Law (n=0.509)', 0.509), ('Power-Law (n=0.452)', 0.452)]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, kinetic_model='power' if 'Power' in kin else 'fickian', power_exp=n_val)
        sens_records.append({
            'sweep_dimension': 'Carbonation Kinetics Model',
            'scenario': kin,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 4. Uptake Stoichiometry: Low vs Midpoint vs High
    for up_sc in ['low', 'midpoint', 'high']:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, uptake_scenario=up_sc)
        sens_records.append({
            'sweep_dimension': 'CO2 Uptake Scenario',
            'scenario': up_sc.capitalize(),
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 5. Compaction Air Void Content: 1.5% vs 2.0% vs 3.0%
    for air_val in [1.5, 2.0, 3.0]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, air_pct=air_val)
        sens_records.append({
            'sweep_dimension': 'Compaction Air Void Content',
            'scenario': f"Air = {air_val:.1f}%",
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'fc=target' if abs(res['pred_fc_MPa'] - (BASE_TARGET + 8.25)) < 0.05 else ('d50=cover' if abs(res['d50_mm'] - BASE_COVER) < 0.2 else 'bounds')
        })

    # 6. SCM Ceiling: SCM <= 50% vs Fly Ash restricted FA <= 35%
    for s_sc, max_fa_val in [('Empirical (SCM<=50%)', 0.50), ('Code-Restricted (FA<=35%)', 0.35)]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, max_fa=max_fa_val)
        sens_records.append({
            'sweep_dimension': 'Fly Ash Code Restriction',
            'scenario': s_sc,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 7. Strength Screening Buffer: IS 10262 Table 2 (s=5.0, +8.25 MPa) vs Table 1 (s=4.0, +6.6 MPa) vs LOO-CV (4.4 MPa) vs Nominal (0 MPa)
    for m_name, m_val in [
        ('IS 10262 Table 2 (s=5, +8.25 MPa)', 8.25),
        ('IS 10262 Table 1 (s=4, +6.6 MPa)', 6.6),
        ('LOO-CV Buffer (+4.4 MPa)', 4.4),
        ('Nominal (0 MPa)', 0.0)
    ]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, margin=m_val)
        sens_records.append({
            'sweep_dimension': 'Strength Buffer Margin',
            'scenario': m_name,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-m_val) < 0.2 else 'bounds')
        })

    # 8. Binder Envelope: Empirical B>=220 vs Structural B>=280
    for b_sc, b_min_val in [('Empirical Envelope (B>=220)', 220.0), ('Restricted Envelope (B>=280)', 280.0)]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=b_min_val, margin=8.25)
        sens_records.append({
            'sweep_dimension': 'Binder Content Lower Bound',
            'scenario': b_sc,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 9. Codified Baseline Framework: EN 206 Baseline (B>=280) vs IS 456 Mild (B>=300) vs IS 456 Severe (B>=320, w/b<=0.45)
    for c_sc, b_min_val, wb_lim in [
        ('EN 206 Baseline (B>=280)', 280.0, 0.55),
        ('IS 456 Mild (B>=300, wb<=0.55)', 300.0, 0.55),
        ('IS 456 Severe (B>=320, wb<=0.45)', 320.0, 0.45)
    ]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=b_min_val, max_wb_override=wb_lim, margin=8.25)
        sens_records.append({
            'sweep_dimension': 'Codified Baseline Framework',
            'scenario': c_sc,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    # 10. Joint Confidence Level Scaling: +1 sigma (~84%) vs 1.645 sigma (95% one-sided)
    for conf_sc, m_val, dur_fac in [
        ('Nominal (0 MPa, 1.00x k)', 0.0, 1.0),
        ('+1 Sigma / 84% (4.4 MPa, 1.15x k)', 4.4, 1.15),
        ('1.645 Sigma / 95% (7.20 MPa, 1.261x k)', 7.20, 1.261),
        ('1.645 Sigma / 95% Corner (7.47 MPa, 1.283x k)', 7.47, 1.283)
    ]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, margin=m_val, durability_factor=dur_fac)
        sens_records.append({
            'sweep_dimension': 'Safety Margin Confidence Level',
            'scenario': conf_sc,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'fc=target' if abs(res['pred_fc_MPa'] - (BASE_TARGET + m_val)) < 0.05 else ('d50=cover' if abs(res['d50_mm']*dur_fac - BASE_COVER) < 0.2 else 'bounds')
        })

    # 11. Superplasticizer Inclusion: Inside Optimizer Objective
    for pce_sc, pce_dose in [('No PCE Added (0%)', 0.0), ('1.0% PCE Inside Optimizer', 0.010)]:
        res = run_continuous_optimizer(BASE_TARGET, BASE_COVER, B_min=BASE_B_STRUCT, pce_dosage=pce_dose)
        sens_records.append({
            'sweep_dimension': 'Superplasticizer PCE Penalty',
            'scenario': pce_sc,
            'optimal_wb': res['w_b'],
            'optimal_B': res['binder_kg_m3'],
            'optimal_FA_pct': res['p_fa_pct'],
            'optimal_SG_pct': res['p_sg_pct'],
            'pred_fc_MPa': res['pred_fc_MPa'],
            'd50_mm': res['d50_mm'],
            'gwp_embodied': res['gwp_embodied'],
            'co2_uptake': res['co2_uptake'],
            'gwp_net': res['gwp_net'],
            'binding_constraint': 'd50=cover' if abs(res['d50_mm']-BASE_COVER) < 0.2 else ('fc=target' if abs(res['pred_fc_MPa']-BASE_TARGET-8.25) < 0.2 else 'bounds')
        })

    df_sens = pd.DataFrame(sens_records)
    df_sens.to_csv('sensitivity_matrix_results.csv', index=False)
    print("Saved sensitivity matrix results to: sensitivity_matrix_results.csv")

    # -----------------------------------------------------------------------------
    # EXTRACTION CHECKS: CORRELATION, VIF, NEAREST MIXES, LEVERAGE, ENVELOPING RANGE
    # -----------------------------------------------------------------------------
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    corr_wb_air = mixes['w_b'].corr(mixes['air_pct'])
    corr_bw_air = mixes['bw'].corr(mixes['air_pct'])
    X_str = sm.add_constant(mixes[['bw', 'air_pct', 'p_FaV', 'p_SgF', 'p_LS', 'p_PoM']])
    vifs = {c: variance_inflation_factor(X_str.values, i) for i, c in enumerate(X_str.columns) if c != 'const'}

    print("\n" + "="*80)
    print("METHODOLOGY VERIFICATION & AUDIT METRICS (ITEMS A2, A3, A4, A5, B1)")
    print("="*80)
    print(f"Correlation w/b vs Air%: {corr_wb_air:.4f}")
    print(f"Correlation B/W vs Air%: {corr_bw_air:.4f}")
    print("VIF values for strength predictors:")
    for k_feat, v_vif in vifs.items():
        print(f"  {k_feat}: {v_vif:.3f}")

    # Nearest mixes in (w/b, air, SCM) space
    opt_wb = 0.45; opt_air = 2.0; opt_fa = 24.04; opt_sg = 25.96
    s_wb = mixes['w_b'].std(); s_air = mixes['air_pct'].std(); s_fa = mixes['p_FaV'].std(); s_sg = mixes['p_SgF'].std()
    mixes_dist = mixes.copy()
    mixes_dist['norm_dist'] = np.sqrt(
        ((mixes_dist['w_b'] - opt_wb)/s_wb)**2 +
        ((mixes_dist['air_pct'] - opt_air)/s_air)**2 +
        ((mixes_dist['p_FaV'] - opt_fa)/s_fa)**2 +
        ((mixes_dist['p_SgF'] - opt_sg)/s_sg)**2
    )
    nearest_df = mixes_dist.sort_values('norm_dist').head(5)
    print("\nTop 5 Nearest Physical Mixes to Benchmark Optimum:")
    for _, nr in nearest_df.iterrows():
        p_fc = predict_strength(nr['w_b'], nr['air_pct'], nr['p_FaV']/100, nr['p_SgF']/100, nr['p_LS']/100, nr['p_PoM']/100)
        p_d50 = predict_k(nr['w_b'], nr['p_FaV']/100, nr['p_SgF']/100, nr['p_LS']/100, nr['p_PoM']/100, condition='sheltered') * np.sqrt(50.0)
        print(f"  {nr['mix_id']} ({nr['notation']}): dist={nr['norm_dist']:.2f} | w/b={nr['w_b']}, air={nr['air_pct']}%, FA={nr['p_FaV']}%, SG={nr['p_SgF']}% | fc meas={nr['fc_28d_MPa']:.1f} vs pred={p_fc:.1f} MPa (err={p_fc-nr['fc_28d_MPa']:+.1f}) | d50 meas={nr['d50_sh_mm']:.1f} vs pred={p_d50:.1f} mm (err={p_d50-nr['d50_sh_mm']:+.1f})")

    print("\nAuthoritative Nearest Mixes Table (C28, C23, C39 vs Benchmark Optimum):")
    print(f"{'Mix':<5} | {'Notation':<24} | {'w/b':<5} | {'Air%':<5} | {'B':<5} | {'FA%':<5} | {'SG%':<5} | {'PO%':<5} | {'fc_meas':<7} | {'fc_pred':<7} | {'fc_err':<7} | {'k_meas':<7} | {'k_pred':<7} | {'d50_meas':<8} | {'d50_pred':<8}")
    print("-" * 140)
    for mid in ['C28', 'C23', 'C39']:
        nr = mixes[mixes['mix_id'] == mid].iloc[0]
        p_fc = predict_strength(nr['w_b'], nr['air_pct'], nr['p_FaV']/100, nr['p_SgF']/100, nr['p_LS']/100, nr['p_PoM']/100)
        p_k = predict_k(nr['w_b'], nr['p_FaV']/100, nr['p_SgF']/100, nr['p_LS']/100, nr['p_PoM']/100, condition='sheltered')
        p_d50 = p_k * np.sqrt(50.0)
        print(f"{mid:<5} | {nr['notation']:<24} | {nr['w_b']:<5.2f} | {nr['air_pct']:<5.1f} | {nr['binder_kg_m3']:<5.0f} | {nr['p_FaV']:<5.1f} | {nr['p_SgF']:<5.1f} | {nr['p_PoM']:<5.1f} | {nr['fc_28d_MPa']:<7.1f} | {p_fc:<7.1f} | {p_fc-nr['fc_28d_MPa']:<+7.1f} | {nr['k_sh']:<7.3f} | {p_k:<7.3f} | {nr['d50_sh_mm']:<8.2f} | {p_d50:<8.2f}")

    # Leverage Check
    X_str_mat = np.column_stack([np.ones(len(mixes)), mixes['bw'], mixes['air_pct'], mixes['p_FaV'], mixes['p_SgF'], mixes['p_LS'], mixes['p_PoM']])
    XtX_inv_str = np.linalg.pinv(X_str_mat.T @ X_str_mat)
    x0_str = np.array([1.0, 1.0/opt_wb, opt_air, opt_fa, opt_sg, 0.0, 0.0])
    h00_str = x0_str.T @ XtX_inv_str @ x0_str
    hbar_str = X_str_mat.shape[1] / X_str_mat.shape[0]

    s_e_val = np.sqrt(m_fc.mse_resid)
    s_pred_val = s_e_val * np.sqrt(1.0 + h00_str)

    X_kin_mat = np.column_stack([np.ones(len(mixes)), mixes['w_b'], mixes['q_FaV'], mixes['q_SgF'], mixes['q_LS'], mixes['q_PoM']])
    XtX_inv_kin = np.linalg.pinv(X_kin_mat.T @ X_kin_mat)
    x0_kin = np.array([1.0, opt_wb, opt_fa/10.0, opt_sg/10.0, 0.0, 0.0])
    h00_kin = x0_kin.T @ XtX_inv_kin @ x0_kin
    hbar_kin = X_kin_mat.shape[1] / X_kin_mat.shape[0]
    print(f"\nLeverage & Prediction Error Check at Optimum:")
    print(f"  Strength Model Leverage: h00 = {h00_str:.4f} (Mean h_bar = {hbar_str:.4f}, 2*h_bar = {2*hbar_str:.4f}) -> {('SAFE' if h00_str < 2*hbar_str else 'EXTRAPOLATION')}")
    print(f"  Standard Error of Prediction: s_pred = s_e * sqrt(1 + h00) = {s_e_val:.4f} * sqrt(1 + {h00_str:.4f}) = {s_pred_val:.2f} MPa (exact {s_pred_val:.4f} MPa)")
    print(f"  Kinetic Model Leverage:  h00 = {h00_kin:.4f} (Mean h_bar = {hbar_kin:.4f}, 2*h_bar = {2*hbar_kin:.4f}) -> {('SAFE' if h00_kin < 2*hbar_kin else 'EXTRAPOLATION')}")

    # Programmatic Enveloping Reductions Across All 18 Scenarios (Item B1 & Item 2)
    # Compare continuous optimum vs best compliant discrete mix under IS 10262 Table 2 (s=5.0, +8.25 MPa)
    pct_reds_nom = []
    pct_reds_pce42 = []
    pct_reds_pce53 = []
    for _, sc_row in df_summary_9cases.iterrows():
        # discrete IS5 nominal vs continuous nominal
        d_gwp = sc_row['Discrete_IS5_Nominal_Net_GWP']
        c_gwp = sc_row['Continuous_Nominal_Net_GWP']
        if not np.isnan(d_gwp) and not np.isnan(c_gwp):
            red_nom = (d_gwp - c_gwp) / d_gwp * 100.0
            red_pce42 = (d_gwp - (c_gwp + 4.2)) / d_gwp * 100.0
            red_pce53 = (d_gwp - (c_gwp + 5.3)) / d_gwp * 100.0
            pct_reds_nom.append(red_nom)
            pct_reds_pce42.append(red_pce42)
            pct_reds_pce53.append(red_pce53)

        # discrete IS5 unc15 vs continuous unc15
        d_buf_gwp = sc_row['Discrete_IS5_Unc15_Net_GWP']
        c_unc_gwp = sc_row['Continuous_Unc15_Net_GWP']
        if not np.isnan(d_buf_gwp) and not np.isnan(c_unc_gwp):
            red_buf = (d_buf_gwp - c_unc_gwp) / d_buf_gwp * 100.0
            red_buf_pce42 = (d_buf_gwp - (c_unc_gwp + 4.2)) / d_buf_gwp * 100.0
            red_buf_pce53 = (d_buf_gwp - (c_unc_gwp + 5.3)) / d_buf_gwp * 100.0
            pct_reds_nom.append(red_buf)
            pct_reds_pce42.append(red_buf_pce42)
            pct_reds_pce53.append(red_buf_pce53)

    min_red_nom, max_red_nom = min(pct_reds_nom), max(pct_reds_nom)
    min_red_pce, max_red_pce = min(pct_reds_pce53), max(pct_reds_pce42)
    print(f"\nItem B1 Recomputed Savings Envelopes across all 18 Scenarios (IS 10262 Margin = 8.25 MPa):")
    print(f"  Before Admixture: {min_red_nom:.2f}% to {max_red_nom:.2f}% (Summary: {min_red_nom:.1f}% to {max_red_nom:.1f}%)")
    print(f"  After 1.0% PCE:    {min_red_pce:.2f}% to {max_red_pce:.2f}% (Summary: {min_red_pce:.1f}% to {max_red_pce:.1f}%)")

    # -----------------------------------------------------------------------------
    # 7. PUBLICATION-QUALITY FIGURES: FIGURE 6 & FIGURE 7
    # -----------------------------------------------------------------------------
    print("\n" + "="*80)
    print("PART E: GENERATING PUBLICATION-QUALITY VISUALIZATIONS")
    print("="*80)

    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 8.5,
        'figure.titlesize': 13,
        'figure.dpi': 300,
        'lines.linewidth': 1.8,
        'axes.spines.top': False,
        'axes.spines.right': False
    })

    # --- FIGURE 6: PARETO FRONTIER (NET GWP vs COMPRESSIVE STRENGTH) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5))

    scm_colors = {
        'OPC_only': '#444444',
        'FaV': '#d2691e',
        'SgF': '#2a7ab0',
        'LS': '#c9a227',
        'PoM': '#7a4fa3',
        'Ternary': '#2e8b57'
    }

    for grp, color in scm_colors.items():
        sub = mixes[mixes['scm_group'] == grp]
        net_vals = [df_discrete_results[df_discrete_results['mix_id']==mid]['net_gwp_sh'].iloc[0] for mid in sub['mix_id']]
        ax1.scatter(sub['fc_28d_MPa'], net_vals,
                    c=color, label=grp, s=70, alpha=0.85, edgecolors='black', linewidth=0.6)

    pareto_ids = ['C24', 'C39', 'C23']
    for pid in pareto_ids:
        row = mixes[mixes['mix_id'] == pid].iloc[0]
        net_val = df_discrete_results[df_discrete_results['mix_id'] == pid]['net_gwp_sh'].iloc[0]
        ax1.scatter(row['fc_28d_MPa'], net_val, s=160, facecolors='none', edgecolors='crimson', linewidth=2.0)
        ax1.annotate(f"{pid}\n({row['notation']})",
                     (row['fc_28d_MPa'], net_val),
                     xytext=(8, -14), textcoords='offset points', fontsize=8,
                     fontweight='bold', color='#111111',
                     arrowprops=dict(arrowstyle="->", color='crimson', lw=1.0))

    ax1.axvline(30.0 + 8.25, color='#777', linestyle='--', alpha=0.7, label='C30/37 Main (38.25 MPa)')
    ax1.axvline(35.0 + 8.25, color='#555', linestyle=':', alpha=0.7, label='C35/45 Main (43.25 MPa)')
    ax1.axvline(40.0 + 8.25, color='#333', linestyle='-.', alpha=0.7, label='C40/50 Main (48.25 MPa)')

    ax1.set_xlabel(r'Measured 28-Day Compressive Strength, $f_{c,28}$ (MPa)')
    ax1.set_ylabel(r'Net Lifecycle Carbon, $GWP_{\mathrm{net}}$ ($\mathrm{kg\ CO_2e / m^3}$)')
    ax1.set_title('(a) Discrete Mix Landscape (45 Physical Mixes, Sheltered)', fontweight='bold')
    ax1.legend(loc='upper left', frameon=True, framealpha=0.9, fontsize=8)
    ax1.set_xlim(20, 65)
    ax1.set_ylim(130, 360)
    ax1.grid(True, linestyle='--', alpha=0.3)

    # Panel B: Continuous Pareto Frontiers across Structural Covers
    fc_span = np.linspace(30.0, 52.0, 25)
    for cov, ls, col in [(25.0, '-.', '#e66101'), (30.0, '-', '#2b83ba'), (35.0, '--', '#2ca25f')]:
        gwp_emp_list = []
        gwp_res_list = []
        for f_target in fc_span:
            r_emp = run_continuous_optimizer(f_target - 8.25, cov, B_min=220.0, margin=8.25)
            r_res = run_continuous_optimizer(f_target - 8.25, cov, B_min=280.0, margin=8.25)
            gwp_emp_list.append(r_emp['gwp_net'] if r_emp['status'] == 'FEASIBLE' else np.nan)
            gwp_res_list.append(r_res['gwp_net'] if r_res['status'] == 'FEASIBLE' else np.nan)
        
        ax2.plot(fc_span, gwp_emp_list, linestyle=ls, color=col, lw=2.2, label=fr'Empirical ($B \geq 220, d={int(cov)}$ mm)')
        ax2.plot(fc_span, gwp_res_list, linestyle=':', color=col, lw=1.6, alpha=0.75, label=fr'Structural ($B \geq 280, d={int(cov)}$ mm)')

    for pid, marker, col in [('C24', 's', '#2a7ab0'), ('C39', '^', '#2e8b57'), ('C23', 'D', '#444444')]:
        row = mixes[mixes['mix_id'] == pid].iloc[0]
        net_val = df_discrete_results[df_discrete_results['mix_id'] == pid]['net_gwp_sh'].iloc[0]
        ax2.scatter(row['fc_28d_MPa'], net_val, s=110, color=col, marker=marker, edgecolors='black', zorder=5,
                    label=f'Discrete {pid} ({row["notation"][:12]})')

    ax2.set_xlabel(r'Required Compressive Strength Threshold, $f_{\mathrm{target}}$ (MPa)')
    ax2.set_ylabel(r'Net Lifecycle Carbon, $GWP_{\mathrm{net}}$ ($\mathrm{kg\ CO_2e / m^3}$)')
    ax2.set_title(r'(b) Continuous Pareto Frontiers ($GWP_{\mathrm{net}}$ vs. $f_c$)', fontweight='bold')
    ax2.legend(loc='upper left', frameon=True, framealpha=0.85, fontsize=7.5)
    ax2.set_xlim(30, 55)
    ax2.set_ylim(95, 230)
    ax2.grid(True, linestyle='--', alpha=0.3)

    plt.tight_layout()
    fig6_path = 'fig6_pareto_carbon_vs_strength.png'
    plt.savefig(fig6_path, dpi=300)
    plt.close()
    print(f"Saved Figure 6 to: {fig6_path}")

    # --- FIGURE 7: SENSITIVITY & ROBUSTNESS ANALYSIS ---
    fig, axes = plt.subplots(1, 4, figsize=(15.0, 6.0))

    # Panel A: Microclimate & SCM Allocation
    ax_a = axes[0]
    alloc_data = df_sens[df_sens['sweep_dimension'].isin(['Exposure Microclimate', 'SCM Allocation Regime'])]
    x_labels = [f"{r['sweep_dimension'].split()[0]}\n{r['scenario']}" for _, r in alloc_data.iterrows()]
    bars_a = ax_a.bar(x_labels, alloc_data['gwp_net'], color=['#3182bd', '#6baed6', '#31a354', '#74c476', '#006d2c'], edgecolor='black', width=0.55)
    ax_a.set_ylabel(r'Net Lifecycle Carbon ($\mathrm{kg\ CO_2e / m^3}$)')
    ax_a.set_title('(a) Microclimate &\nSCM allocation', fontweight='bold')
    ax_a.set_ylim(110, 150)
    for bar in bars_a:
        yval = bar.get_height()
        ax_a.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"{yval:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax_a.grid(True, axis='y', linestyle='--', alpha=0.4)

    # Panel B: Kinetics Model & Uptake Scenarios
    ax_b = axes[1]
    kin_data = df_sens[df_sens['sweep_dimension'].isin(['Carbonation Kinetics Model', 'CO2 Uptake Scenario'])]
    x_labels_b = []
    for _, r in kin_data.iterrows():
        if r['sweep_dimension'] == 'CO2 Uptake Scenario':
            x_labels_b.append(r['scenario'])
        else:
            parts = r['scenario'].split()
            x_labels_b.append(f"{parts[0]}\n{' '.join(parts[1:])}")
    bars_b = ax_b.bar(x_labels_b, kin_data['gwp_net'], color=['#e6550d', '#fdae6b', '#feedde', '#756bb1', '#bcbddc', '#dadaeb'], edgecolor='black', width=0.55)
    ax_b.set_ylabel(r'Net Lifecycle Carbon ($\mathrm{kg\ CO_2e / m^3}$)')
    ax_b.set_title('(b) Carbonation kinetics\n& CO2 uptake', fontweight='bold')
    ax_b.set_ylim(110, 150)
    for bar in bars_b:
        yval = bar.get_height()
        ax_b.text(bar.get_x() + bar.get_width()/2.0, yval + 0.6, f"{yval:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax_b.grid(True, axis='y', linestyle='--', alpha=0.4)

    # Panel C: Compaction Air & Strength Safety Margin
    ax_c = axes[2]
    air_data = df_sens[df_sens['sweep_dimension'].isin(['Compaction Air Void Content', 'Strength Buffer Margin'])]
    x_labels_c = []
    for _, r in air_data.iterrows():
        sc = r['scenario']
        if 'Air =' in sc:
            x_labels_c.append(sc.replace('Air = ', 'Air\n'))
        elif 's=5' in sc:
            x_labels_c.append("IS 10262\n+8.25 MPa")
        elif 's=4' in sc:
            x_labels_c.append("IS 10262\n+6.6 MPa")
        elif 'LOO-CV' in sc or 'Buffer' in sc or 'Heuristic' in sc:
            x_labels_c.append("LOO-CV\n(+4.4 MPa)")
        elif 'Nominal' in sc:
            x_labels_c.append("Nominal\n(0 MPa)")
        else:
            x_labels_c.append(sc)
    colors_c = ['#de2d26', '#fc9272', '#fee0d2', '#252525', '#525252', '#737373', '#969696'][:len(x_labels_c)]
    bars_c = ax_c.bar(x_labels_c, air_data['gwp_net'], color=colors_c, edgecolor='black', width=0.55)
    ax_c.set_ylabel(r'Net Lifecycle Carbon ($\mathrm{kg\ CO_2e / m^3}$)')
    ax_c.set_title('(c) Compaction air\n& strength margin', fontweight='bold')
    ax_c.set_ylim(110, 150)
    for bar in bars_c:
        yval = bar.get_height()
        ax_c.text(bar.get_x() + bar.get_width()/2.0, yval + 0.6, f"{yval:.1f}", ha='center', va='bottom', fontsize=8, fontweight='bold')
    ax_c.grid(True, axis='y', linestyle='--', alpha=0.4)

    # Panel D: Codified Baseline Framework & Code FA Restriction
    ax_d = axes[3]
    code_data = df_sens[df_sens['sweep_dimension'].isin(['Codified Baseline Framework', 'Fly Ash Code Restriction'])]
    x_labels_d = []
    for _, r in code_data.iterrows():
        sc = r['scenario']
        if 'EN 206' in sc:
            x_labels_d.append("EN 206\nBaseline")
        elif 'IS 456 Mild' in sc:
            x_labels_d.append("IS 456 Mild\n(B>=300)")
        elif 'IS 456 Severe' in sc:
            x_labels_d.append("IS 456 Severe\n(B>=320)")
        elif 'Empirical' in sc:
            x_labels_d.append("Empirical\n(SCM<=50%)")
        elif 'Code-Restricted' in sc:
            x_labels_d.append("PPC Limit\n(FA<=35%)")
        else:
            x_labels_d.append(sc)
    colors_d = ['#2ca25f', '#66c2a4', '#b2e2e2', '#8856a7', '#9ebcda'][:len(x_labels_d)]
    bars_d = ax_d.bar(x_labels_d, code_data['gwp_net'], color=colors_d, edgecolor='black', width=0.55)
    ax_d.set_ylabel(r'Net Lifecycle Carbon ($\mathrm{kg\ CO_2e / m^3}$)')
    ax_d.set_title('(d) Binder minimum\n& PPC fly ash cap', fontweight='bold')
    ax_d.set_ylim(95, 160)
    for bar in bars_d:
        yval = bar.get_height()
        ax_d.text(bar.get_x() + bar.get_width()/2.0, yval + 0.8, f"{yval:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax_d.grid(True, axis='y', linestyle='--', alpha=0.4)

    # Reserve space for category labels at the manuscript's printed size.
    for ax in axes:
        ax.set_title(ax.get_title(), fontsize=11, pad=12)
        ax.tick_params(axis='x', labelsize=9, rotation=55)
        ax.tick_params(axis='y', labelsize=9)
        for label in ax.get_xticklabels():
            label.set_horizontalalignment('right')
            label.set_rotation_mode('anchor')
        ax.set_ylabel(r'Net lifecycle carbon (kg CO$_2$e/m$^3$)', fontsize=10)
        ax.margins(x=0.08)
    fig.subplots_adjust(left=0.055, right=0.99, bottom=0.26, top=0.86, wspace=0.40)
    fig7_path = 'fig7_sensitivity_analysis.png'
    plt.savefig(fig7_path, dpi=300)
    plt.close()
    print(f"Saved Figure 7 to: {fig7_path}")

    print("\n" + "="*80)
    print("ALL OPTIMIZATION WORKFLOW STEPS EXECUTED SUCCESSFULLY!")
    print("="*80)

if __name__ == '__main__':
    main()
