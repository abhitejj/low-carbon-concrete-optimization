import os
import openpyxl
import pandas as pd
import numpy as np

# Input file path
raw_path = '/Users/abhitej/Desktop/Sem7/MESS/Project/10-year natural carbonation of concretes with limestone, fly ash, volcanic ash, and slag and exposed to tropical climate in India/Natural carbonation data/Natural carbonation depths of 45 concretes v2.xlsx'

wb = openpyxl.load_workbook(raw_path, data_only=True)
wsA = wb['A. Mix proportions']
wsB = wb['B. Sheltered conditions']
wsC = wb['C. Unsheltered conditions']

# Emission factors (cradle-to-gate in kg CO2e / kg)
# Sourced from Ecoinvent 3.8, ICE v3.0, and fib Model Code 2020 / Indian CMA
EF = {
    'opc': 0.840,         # Ordinary Portland Cement (CEM I / OPC 53)
    'fa': 0.015,          # Fly ash (Class F, dry collection, beneficiation, transport)
    'sg': 0.060,          # Slag / GGBS (granulation, drying, fine grinding)
    'ls': 0.025,          # Limestone powder (quarrying, drying, fine grinding)
    'po': 0.030,          # Volcanic ash / Natural pozzolan (quarrying, calcining/grinding)
    'sand': 0.006,        # Fine aggregate (natural/crushed sand)
    'gravel': 0.006,      # Coarse aggregate (crushed stone)
    'water': 0.0005,      # Batching water
    'batching_m3': 7.5    # Ready-mix concrete plant operations per m3
}

# Parse Mix proportions (Sheet A)
mix_dict = {}

for r in range(3, wsA.max_row + 1):
    mid = wsA.cell(r, 1).value
    if not mid:
        continue
    notat = wsA.cell(r, 2).value.strip()
    cast_date = wsA.cell(r, 3).value
    start_date = wsA.cell(r, 4).value
    add_str = str(wsA.cell(r, 5).value).strip()
    wb_val = float(wsA.cell(r, 6).value)
    binder = float(wsA.cell(r, 7).value)
    sand = float(wsA.cell(r, 8).value)
    gravel = float(wsA.cell(r, 9).value)
    air = float(wsA.cell(r, 10).value)
    fc = float(wsA.cell(r, 11).value)
    curing_days = int(wsA.cell(r, 12).value)
    
    # Parse SCM percentages
    p_fa = 0.0; p_sg = 0.0; p_ls = 0.0; p_po = 0.0
    scm_category = 'NoSCM'
    
    if 'FaV' in notat and 'SgF' in notat:
        scm_category = 'SgF+FaV'
        p_sg = 20.0; p_fa = 20.0
    elif 'FaV' in notat and 'PoM' in notat:
        scm_category = 'FaV+PoM'
        p_fa = 20.0; p_po = 20.0
    elif 'SgF' in notat and 'PoM' in notat:
        scm_category = 'SgF+PoM'
        p_sg = 20.0; p_po = 20.0
    elif 'FaV' in notat:
        scm_category = 'FaV'
        if '50FaV' in notat: p_fa = 50.0
        elif '30FaV' in notat: p_fa = 30.0
        elif '15FaV' in notat: p_fa = 15.0
    elif 'SgF' in notat:
        scm_category = 'SgF'
        if '50SgF' in notat: p_sg = 50.0
        elif '30SgF' in notat: p_sg = 30.0
        elif '15SgF' in notat: p_sg = 15.0
    elif 'LS' in notat:
        scm_category = 'LS'
        if '30LS' in notat: p_ls = 30.0
        elif '11LS' in notat: p_ls = 11.0
    elif 'PoM' in notat:
        scm_category = 'PoM'
        if '30PoM' in notat: p_po = 30.0
        elif '15PoM' in notat: p_po = 15.0
        elif '13PoM' in notat or mid == 'C45': p_po = 13.0 if '13 %' in add_str else 15.0
        
    p_scm_tot = p_fa + p_sg + p_ls + p_po
    p_opc = 100.0 - p_scm_tot
    
    m_opc = binder * (p_opc / 100.0)
    m_fa = binder * (p_fa / 100.0)
    m_sg = binder * (p_sg / 100.0)
    m_ls = binder * (p_ls / 100.0)
    m_po = binder * (p_po / 100.0)
    m_scm_tot = binder * (p_scm_tot / 100.0)
    water = wb_val * binder
    
    # Calculate embodied carbon (GWP in kg CO2e / m3)
    co2_mat = (m_opc * EF['opc'] + m_fa * EF['fa'] + m_sg * EF['sg'] +
               m_ls * EF['ls'] + m_po * EF['po'] + sand * EF['sand'] +
               gravel * EF['gravel'] + water * EF['water'])
    gwp_total = co2_mat + EF['batching_m3']
    ci_per_mpa = gwp_total / fc
    
    cast_str = cast_date.strftime('%Y-%m-%d') if hasattr(cast_date, 'strftime') else str(cast_date)[:10]
    start_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else str(start_date)[:10]
    
    mix_dict[mid] = {
        'mix_id': mid,
        'notation': notat,
        'cement_type': 'CmS (CEM I OPC)',
        'scm_category': scm_category,
        'total_scm_pct': p_scm_tot,
        'opc_pct': p_opc,
        'fa_pct': p_fa,
        'sg_pct': p_sg,
        'ls_pct': p_ls,
        'po_pct': p_po,
        'wb_ratio': wb_val,
        'binder_content_kg_m3': binder,
        'opc_kg_m3': round(m_opc, 2),
        'scm_kg_m3': round(m_scm_tot, 2),
        'fa_kg_m3': round(m_fa, 2),
        'sg_kg_m3': round(m_sg, 2),
        'ls_kg_m3': round(m_ls, 2),
        'po_kg_m3': round(m_po, 2),
        'water_kg_m3': round(water, 2),
        'sand_kg_m3': sand,
        'gravel_kg_m3': gravel,
        'air_content_pct': air,
        'fc_28d_mpa': fc,
        'curing_time_days': curing_days,
        'casting_date': cast_str,
        'exposure_start_date': start_str,
        'embodied_gwp_kgco2e_m3': round(gwp_total, 2),
        'carbon_intensity_kgco2e_m3_mpa': round(ci_per_mpa, 2)
    }

# Process Longitudinal Measurements (Sheets B & C)
long_rows = []

for cond, ws in [('Sheltered', wsB), ('Unsheltered', wsC)]:
    for r in range(3, ws.max_row + 1):
        mid = ws.cell(r, 1).value
        if not mid or mid not in mix_dict:
            continue
        mix_info = mix_dict[mid]
        
        for ep in range(6):
            base = 4 + ep * 4
            d_meas = ws.cell(r, base).value
            t_exp = ws.cell(r, base + 1).value
            d_mean = ws.cell(r, base + 2).value
            d_sd = ws.cell(r, base + 3).value
            
            # Skip unmeasured / missing entries
            if d_mean is None or d_mean == '-' or str(d_mean).strip() == '':
                continue
            
            d_mean_f = float(d_mean)
            d_sd_f = float(d_sd) if (d_sd is not None and d_sd != '-') else np.nan
            t_exp_f = float(t_exp)
            meas_str = d_meas.strftime('%Y-%m-%d') if hasattr(d_meas, 'strftime') else str(d_meas)[:10]
            
            sqrt_t = np.sqrt(t_exp_f)
            inst_k = d_mean_f / sqrt_t if sqrt_t > 0 else np.nan
            
            row = dict(mix_info)
            row.update({
                'exposure_condition': cond,
                'measurement_epoch': ep + 1,
                'measurement_date': meas_str,
                'exposure_time_years': round(t_exp_f, 4),
                'sqrt_exposure_time': round(sqrt_t, 4),
                'carbonation_depth_mm': round(d_mean_f, 4),
                'carbonation_depth_sd_mm': round(d_sd_f, 4) if not np.isnan(d_sd_f) else np.nan,
                'instantaneous_k_mm_per_yr05': round(inst_k, 4)
            })
            long_rows.append(row)

df_long = pd.DataFrame(long_rows)
out_long_csv = '/Users/abhitej/Desktop/Sem7/MESS/Project/cleaned_concrete_carbonation_dataset.csv'
df_long.to_csv(out_long_csv, index=False)
print(f'Successfully wrote {len(df_long)} rows to {out_long_csv}')

# Now fit carbonation kinetics per mix per condition
mix_summary_rows = []

for mid in sorted(mix_dict.keys(), key=lambda x: int(x[1:])):
    minfo = dict(mix_dict[mid])
    
    for cond in ['Sheltered', 'Unsheltered']:
        sub = df_long[(df_long['mix_id'] == mid) & (df_long['exposure_condition'] == cond)]
        c_prefix = cond.lower()
        if len(sub) >= 2:
            t_arr = sub['exposure_time_years'].values
            d_arr = sub['carbonation_depth_mm'].values
            sqrt_t = np.sqrt(t_arr)
            
            # k through origin: k = sum(sqrt_t * d) / sum(t)
            k_val = np.sum(sqrt_t * d_arr) / np.sum(t_arr)
            d_pred = k_val * sqrt_t
            ss_tot = np.sum((d_arr - np.mean(d_arr))**2)
            ss_res = np.sum((d_arr - d_pred)**2)
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
            
            # Power law: log(d) = log(a) + n * log(t)
            if np.all(d_arr > 0):
                p = np.polyfit(np.log(t_arr), np.log(d_arr), 1)
                n_pow = p[0]
                a_pow = np.exp(p[1])
            else:
                n_pow, a_pow = np.nan, np.nan
                
            max_t = np.max(t_arr)
            max_d = np.max(d_arr)
            d50 = k_val * np.sqrt(50.0)
            life_30mm = (30.0 / k_val)**2 if k_val > 0 else np.nan
            life_25mm = (25.0 / k_val)**2 if k_val > 0 else np.nan
        else:
            k_val, r2, n_pow, a_pow, max_t, max_d, d50, life_30mm, life_25mm = (
                np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan)
        
        minfo.update({
            f'{c_prefix}_obs_points': len(sub),
            f'{c_prefix}_k_mm_yr05': round(k_val, 3) if not np.isnan(k_val) else np.nan,
            f'{c_prefix}_r2': round(r2, 4) if not np.isnan(r2) else np.nan,
            f'{c_prefix}_n_power': round(n_pow, 3) if not np.isnan(n_pow) else np.nan,
            f'{c_prefix}_a_power': round(a_pow, 3) if not np.isnan(a_pow) else np.nan,
            f'{c_prefix}_max_exposure_yrs': round(max_t, 2) if not np.isnan(max_t) else np.nan,
            f'{c_prefix}_max_depth_mm': round(max_d, 2) if not np.isnan(max_d) else np.nan,
            f'{c_prefix}_projected_50yr_depth_mm': round(d50, 1) if not np.isnan(d50) else np.nan,
            f'{c_prefix}_service_life_25mm_cover_yrs': round(life_25mm, 1) if not np.isnan(life_25mm) else np.nan,
            f'{c_prefix}_service_life_30mm_cover_yrs': round(life_30mm, 1) if not np.isnan(life_30mm) else np.nan,
        })
    mix_summary_rows.append(minfo)

df_summary = pd.DataFrame(mix_summary_rows)
out_summary_csv = '/Users/abhitej/Desktop/Sem7/MESS/Project/cleaned_mix_summary_and_fitted_carbonation.csv'
df_summary.to_csv(out_summary_csv, index=False)
print(f'Successfully wrote {len(df_summary)} mix summaries to {out_summary_csv}')
