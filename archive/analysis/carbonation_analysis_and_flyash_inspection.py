import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set publication style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica', 'Arial', 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['font.size'] = 11

project_dir = '/Users/abhitej/Desktop/Sem7/MESS/Project'
long_csv = os.path.join(project_dir, 'cleaned_concrete_carbonation_dataset.csv')
summary_csv = os.path.join(project_dir, 'cleaned_mix_summary_and_fitted_carbonation.csv')

df_long = pd.read_csv(long_csv)
df_sum = pd.read_csv(summary_csv)

print(f"Loaded {len(df_long)} longitudinal records and {len(df_sum)} mix summaries.")

# -------------------------------------------------------------
# Figure 1: Carbonation depth vs sqrt(time) - Sheltered vs Unsheltered
# -------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

colors = {
    'NoSCM': '#2b5c8f',
    'FaV': '#d95f02',
    'SgF': '#7570b3',
    'LS': '#1b9e77',
    'PoM': '#e7298a',
    'SgF+FaV': '#e6ab02',
    'FaV+PoM': '#a6761d',
    'SgF+PoM': '#666666'
}

for ax, cond in zip(axes, ['Sheltered', 'Unsheltered']):
    sub = df_long[df_long['exposure_condition'] == cond]
    for mid, group in sub.groupby('mix_id'):
        scm_cat = group['scm_category'].iloc[0]
        c = colors.get(scm_cat, '#999999')
        lw = 2.2 if scm_cat in ['FaV', 'NoSCM'] else 1.0
        alpha = 0.85 if scm_cat in ['FaV', 'NoSCM'] else 0.45
        
        # Sort by exposure time
        group = group.sort_values('exposure_time_years')
        # Add origin (0, 0)
        t_vals = np.concatenate([[0], group['exposure_time_years'].values])
        d_vals = np.concatenate([[0], group['carbonation_depth_mm'].values])
        ax.plot(np.sqrt(t_vals), d_vals, color=c, lw=lw, alpha=alpha, marker='o' if scm_cat == 'FaV' else 'None', markersize=4)

    ax.set_title(f'{cond} Exposure (Tropical Chennai)', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel(r'$\sqrt{\mathrm{Exposure\ Time}}\ (\mathrm{years}^{0.5})$', fontsize=12)
    ax.set_xlim(0, 3.8)
    ax.set_ylim(0, 30)

    # Reference cover depth lines
    ax.axhline(25, color='red', linestyle='--', alpha=0.6, label='25 mm Cover (IS 456 Moderate)')
    ax.axhline(30, color='darkred', linestyle=':', alpha=0.7, label='30 mm Cover (IS 456 Severe)')

axes[0].set_ylabel(r'Mean Carbonation Depth $d_{\mathrm{CO}_2}\ (\mathrm{mm})$', fontsize=12)

# Custom legend
custom_lines = [
    plt.Line2D([0], [0], color=colors['NoSCM'], lw=2.5, label='OPC Control (No SCM)'),
    plt.Line2D([0], [0], color=colors['FaV'], lw=2.5, marker='o', label='Fly Ash (FaV) Mixes'),
    plt.Line2D([0], [0], color=colors['SgF'], lw=1.5, label='Slag (SgF) Mixes'),
    plt.Line2D([0], [0], color=colors['LS'], lw=1.5, label='Limestone (LS) Mixes'),
    plt.Line2D([0], [0], color=colors['PoM'], lw=1.5, label='Volcanic Ash (PoM)'),
    plt.Line2D([0], [0], color='red', lw=1.5, linestyle='--', label='25 mm Cover Limit'),
]
axes[0].legend(handles=custom_lines, loc='upper left', frameon=True, fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(project_dir, 'fig1_carbonation_kinetics_by_condition.png'), dpi=300)
plt.close(fig)
print("Saved fig1_carbonation_kinetics_by_condition.png")

# -------------------------------------------------------------
# Figure 2: The Fly Ash Trade-off: Strength vs Carbonation vs Embodied Carbon
# -------------------------------------------------------------
# Mix series with B=310 kg/m3, w/b=0.50: C5 (0%), C33 (15%), C34 (30%), C35 (50%)
fa_iso = df_sum[df_sum['mix_id'].isin(['C5', 'C33', 'C34', 'C35'])].sort_values('fa_pct')

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

# Plot 1: Compressive Strength
ax1.plot(fa_iso['fa_pct'], fa_iso['fc_28d_mpa'], marker='s', color='#2b5c8f', lw=2.5, markersize=8)
for _, r in fa_iso.iterrows():
    ax1.annotate(f"{r['fc_28d_mpa']:.1f} MPa", (r['fa_pct'], r['fc_28d_mpa'] + 0.8), ha='center', fontweight='bold')
ax1.set_xlabel('Fly Ash Replacement Level (%)', fontsize=12)
ax1.set_ylabel('28-Day Compressive Strength $f_c$ (MPa)', fontsize=12)
ax1.set_title('28-Day Strength Dilution\n(Fixed B=310, w/b=0.50)', fontsize=13, fontweight='bold')
ax1.set_ylim(20, 55)

# Plot 2: Carbonation Rate k
ax2.plot(fa_iso['fa_pct'], fa_iso['sheltered_k_mm_yr05'], marker='o', color='#d95f02', lw=2.5, markersize=8, label='Sheltered')
ax2.plot(fa_iso['fa_pct'], fa_iso['unsheltered_k_mm_yr05'], marker='^', color='#1b9e77', lw=2.5, markersize=8, label='Unsheltered')
for _, r in fa_iso.iterrows():
    ax2.annotate(f"{r['sheltered_k_mm_yr05']:.2f}", (r['fa_pct'], r['sheltered_k_mm_yr05'] + 0.25), color='#d95f02', ha='center', fontweight='bold')
    ax2.annotate(f"{r['unsheltered_k_mm_yr05']:.2f}", (r['fa_pct'], r['unsheltered_k_mm_yr05'] - 0.5), color='#1b9e77', ha='center', fontweight='bold')
ax2.set_xlabel('Fly Ash Replacement Level (%)', fontsize=12)
ax2.set_ylabel(r'Carbonation Rate $k\ (\mathrm{mm}/\mathrm{year}^{0.5})$', fontsize=12)
ax2.set_title('Accelerating Carbonation Rate\n(Severe Sheltered Vulnerability)', fontsize=13, fontweight='bold')
ax2.legend(frameon=True, loc='upper left')
ax2.set_ylim(1.0, 9.0)

# Plot 3: Embodied Carbon (GWP)
ax3.plot(fa_iso['fa_pct'], fa_iso['embodied_gwp_kgco2e_m3'], marker='D', color='#7570b3', lw=2.5, markersize=8)
for _, r in fa_iso.iterrows():
    ax3.annotate(f"{r['embodied_gwp_kgco2e_m3']:.1f} kg", (r['fa_pct'], r['embodied_gwp_kgco2e_m3'] + 5), ha='center', fontweight='bold')
ax3.set_xlabel('Fly Ash Replacement Level (%)', fontsize=12)
ax3.set_ylabel(r'Embodied Carbon $\mathrm{GWP}\ (\mathrm{kg\ CO_2e/m^3})$', fontsize=12)
ax3.set_title('Substantial Carbon Reductions\n(-46% at 50% Replacement)', fontsize=13, fontweight='bold')
ax3.set_ylim(130, 310)

fig.tight_layout()
fig.savefig(os.path.join(project_dir, 'fig2_fly_ash_tradeoff_isoparametric.png'), dpi=300)
plt.close(fig)
print("Saved fig2_fly_ash_tradeoff_isoparametric.png")

# -------------------------------------------------------------
# Figure 3: Optimization Landscape: Embodied Carbon vs Strength vs Carbonation
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 7))

scatter = ax.scatter(
    df_sum['fc_28d_mpa'],
    df_sum['embodied_gwp_kgco2e_m3'],
    c=df_sum['sheltered_k_mm_yr05'],
    cmap='viridis_r',
    s=df_sum['total_scm_pct'] * 4 + 40,
    edgecolor='#333333',
    linewidth=0.8,
    alpha=0.9
)
cbar = fig.colorbar(scatter, ax=ax)
cbar.set_label(r'Sheltered Carbonation Rate $k_{\mathrm{sh}}\ (\mathrm{mm}/\mathrm{year}^{0.5})$', fontsize=11)

# Annotate key mixes
annot_keys = ['C1', 'C5', 'C8', 'C9', 'C22', 'C24', 'C29', 'C33', 'C34', 'C35']
for _, r in df_sum[df_sum['mix_id'].isin(annot_keys)].iterrows():
    ax.annotate(r['mix_id'], (r['fc_28d_mpa'] + 0.6, r['embodied_gwp_kgco2e_m3'] - 2), fontsize=9, fontweight='bold', color='#111111')

ax.set_xlabel('28-Day Compressive Strength $f_c$ (MPa)', fontsize=12)
ax.set_ylabel(r'Embodied Carbon $\mathrm{GWP}\ (\mathrm{kg\ CO_2e/m^3})$', fontsize=12)
ax.set_title('Concrete Optimization Landscape: Strength, Carbon & Carbonation\n(Circle size proportional to SCM %)', fontsize=13, fontweight='bold')

# Feasibility boundary indication
ax.axvline(30, color='gray', linestyle=':', alpha=0.7)
ax.annotate('Structural Target C30/37 ($f\'_c = 30$ MPa)', (30.5, 330), color='gray', fontsize=10, fontstyle='italic')

fig.tight_layout()
for d in [project_dir, os.path.dirname(os.path.abspath(__file__))]:
    fig.savefig(os.path.join(d, 'fig3_optimization_tradeoff_landscape.png'), dpi=300)
plt.close(fig)
print("Saved fig3_optimization_tradeoff_landscape.png")

# -------------------------------------------------------------
# Figure 4: Compressive Strength Verification
# -------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Bolomey Law (fc vs B/W)
bw_ratio = 1.0 / df_sum['wb_ratio']
scatter1 = ax1.scatter(bw_ratio, df_sum['fc_28d_mpa'], c=df_sum['air_content_pct'], cmap='coolwarm', s=70, edgecolor='black', linewidth=0.6)
cbar1 = fig.colorbar(scatter1, ax=ax1)
cbar1.set_label('Air Content (%)', fontsize=11)

p_bw = np.polyfit(bw_ratio, df_sum['fc_28d_mpa'], 1)
x_line = np.linspace(bw_ratio.min(), bw_ratio.max(), 50)
r2_bw_raw = np.corrcoef(bw_ratio, df_sum['fc_28d_mpa'])[0, 1]**2
ax1.plot(x_line, np.polyval(p_bw, x_line), 'k--', lw=1.8, label=f'Raw Trend ($R^2={r2_bw_raw:.3f}$, uncorrected)')

ax1.set_xlabel(r'Binder-to-Water Ratio $(B/W = 1/(w/b))$', fontsize=12)
ax1.set_ylabel('28-Day Compressive Strength $f_c$ (MPa)', fontsize=12)
ax1.set_title('Raw Strength vs $B/W$ (Confounded by High Air)', fontsize=13, fontweight='bold')
ax1.legend(loc='upper left', frameon=True)

# Air-corrected strength
# From OLS regression: fc_corr = fc - (-4.45 * (air - 2.0))
fc_corr = df_sum['fc_28d_mpa'] + 4.4512 * (df_sum['air_content_pct'] - 2.0)
scatter2 = ax2.scatter(bw_ratio, fc_corr, c=df_sum['total_scm_pct'], cmap='plasma', s=70, edgecolor='black', linewidth=0.6)
cbar2 = fig.colorbar(scatter2, ax=ax2)
cbar2.set_label('Total SCM (%)', fontsize=11)

p_corr = np.polyfit(bw_ratio, fc_corr, 1)
ax2.plot(x_line, np.polyval(p_corr, x_line), 'b-', lw=2.0, label=r'Air-Normalized Bolomey Model ($2\%$ Air baseline)')

ax2.set_xlabel(r'Binder-to-Water Ratio $(B/W = 1/(w/b))$', fontsize=12)
ax2.set_ylabel(r'Air-Normalized Strength $f_{c,\mathrm{norm}}$ (MPa)', fontsize=12)
ax2.set_title('Air-Normalized Strength vs $B/W$\n(Restores Fundamental Bolomey Relation)', fontsize=13, fontweight='bold')
ax2.legend(loc='upper left', frameon=True)

fig.tight_layout()
for d in [project_dir, os.path.dirname(os.path.abspath(__file__))]:
    fig.savefig(os.path.join(d, 'fig4_strength_verification_abrams_air.png'), dpi=300)
plt.close(fig)
print("Saved fig4_strength_verification_abrams_air.png")

# -------------------------------------------------------------
# Figure 5: Sheltered vs Unsheltered Carbonation Divergence
# -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 8))

for scm_cat, group in df_sum.groupby('scm_category'):
    c = colors.get(scm_cat, '#999999')
    ax.scatter(group['unsheltered_k_mm_yr05'], group['sheltered_k_mm_yr05'], color=c, label=scm_cat, s=65, edgecolor='black', linewidth=0.6, alpha=0.85)

# 1:1 line
lims = [1, 9]
ax.plot(lims, lims, 'k--', lw=1.5, label='1:1 Line (Equal Carbonation)')
# Regression line
p_env = np.polyfit(df_sum['unsheltered_k_mm_yr05'], df_sum['sheltered_k_mm_yr05'], 1)
ax.plot(lims, np.polyval(p_env, lims), 'r-', lw=1.8, label=f'Empirical Trend ($k_{{sh}} = {p_env[0]:.2f} k_{{un}} + {p_env[1]:.2f}$)')

# Service life threshold boxes (e.g. 50-year service life with 30mm cover requires k <= 30 / sqrt(50) = 4.24 mm/yr^0.5)
k_crit = 30.0 / np.sqrt(50.0) # 4.24 mm/yr^0.5
ax.axhline(k_crit, color='darkred', linestyle=':', alpha=0.7)
ax.axvline(k_crit, color='darkred', linestyle=':', alpha=0.7)
ax.annotate(r'$k_{\mathrm{crit}}$ for 30 mm Cover @ 50 yr ($4.24\ \mathrm{mm}/\mathrm{yr}^{0.5}$)', (1.2, k_crit + 0.15), color='darkred', fontsize=10, fontweight='bold')

ax.set_xlabel(r'Unsheltered Carbonation Rate $k_{\mathrm{un}}\ (\mathrm{mm}/\mathrm{year}^{0.5})$', fontsize=12)
ax.set_ylabel(r'Sheltered Carbonation Rate $k_{\mathrm{sh}}\ (\mathrm{mm}/\mathrm{year}^{0.5})$', fontsize=12)
ax.set_title('Tropical Carbonation Divergence: Sheltered vs Unsheltered\n(Chennai Exposure: Monsoon Rain Retards Unsheltered Carbonation)', fontsize=13, fontweight='bold')
ax.set_xlim(1, 8)
ax.set_ylim(1, 9)
ax.legend(frameon=True, loc='lower right', fontsize=10)

fig.tight_layout()
fig.savefig(os.path.join(project_dir, 'fig5_sheltered_vs_unsheltered_divergence.png'), dpi=300)
plt.close(fig)
print("Saved fig5_sheltered_vs_unsheltered_divergence.png")

print("All 5 analysis figures successfully generated in Project directory!")
