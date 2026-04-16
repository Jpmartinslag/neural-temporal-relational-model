import pandas as pd
import numpy as np
import json
import os
from pathlib import Path

def audit_robust_correlations():
    # Paths
    panel_path = 'data/processed/extended_panel_core_v0.csv'
    output_report_path = 'reports/FORWARD_LOOKING_SIGNAL_AUDIT_V0.md'

    # 1. Load Extended Panel
    df = pd.read_csv(panel_path, dtype={'ze2020': str})

    # 2. Prepare Target Growth (Annual)
    # Target is side_establishment_creations_official
    df = df.sort_values(['ze2020', 'year'])
    df['target_growth'] = df.groupby('ze2020')['side_establishment_creations_official'].pct_change()

    # Remove inf/nan from growth
    df = df.replace([np.inf, -np.inf], np.nan)

    # Features to test
    signals = [
        'regime_signal_jan_mar',
        'regime_signal_jan_jun',
        'regime_signal_jan_sep',
        'regime_signal_jan_dec',
        'regime_signal_lag_1'
    ]

    results = []

    # A. Pooled Correlations
    for sig in signals:
        valid = df[[sig, 'target_growth']].dropna()
        if len(valid) > 0:
            corr = valid[sig].corr(valid['target_growth'])
            results.append({
                'type': 'Pooled',
                'signal': sig,
                'year': 'All',
                'n': len(valid),
                'correlation': corr
            })

    # B. Within-Year Correlations (Demeaned by Year)
    for sig in signals:
        df_clean = df[[sig, 'target_growth', 'year']].dropna().copy()
        if len(df_clean) == 0: continue

        # Demean
        df_clean['sig_demeaned'] = df_clean[sig] - df_clean.groupby('year')[sig].transform('mean')
        df_clean['target_demeaned'] = df_clean['target_growth'] - df_clean.groupby('year')['target_growth'].transform('mean')

        corr = df_clean['sig_demeaned'].corr(df_clean['target_demeaned'])
        results.append({
            'type': 'Within-Year (Demeaned)',
            'signal': sig,
            'year': 'All',
            'n': len(df_clean),
            'correlation': corr
        })

    # C. Per Year Correlations
    for yr in sorted(df['year'].unique()):
        df_yr = df[df['year'] == yr]
        for sig in signals:
            valid = df_yr[[sig, 'target_growth']].dropna()
            if len(valid) > 10: # Minimum sample size
                corr = valid[sig].corr(valid['target_growth'])
                results.append({
                    'type': 'Per-Year',
                    'signal': sig,
                    'year': yr,
                    'n': len(valid),
                    'correlation': corr
                })

    # 3. Generate Markdown Report
    df_results = pd.DataFrame(results)

    report = [
        "# Forward-looking Signal Audit v1 (Robust)",
        "",
        "## Methodology",
        "- **Signals:** Multi-horizon national shocks projected via zone sectoral profile (FLORES A17).",
        "- **Target:** Annual growth of SIDE business creations (local).",
        "- **Demeaning:** Within-year correlation removes the national trend to see if the signal captures territorial variance.",
        "",
        "## Summary Results",
        ""
    ]

    # Summary Table (Pooled and Demeaned)
    summary = df_results[df_results['type'].isin(['Pooled', 'Within-Year (Demeaned)'])]
    report.append("| Signal | Type | Correlation | N |")
    report.append("| :--- | :--- | :---: | :---: |")
    for _, r in summary.iterrows():
        report.append(f"| {r['signal']} | {r['type']} | {r['correlation']:.4f} | {r['n']} |")

    report.append("\n## Per-Year Detail\n")
    report.append("| Year | Signal | Correlation | N |")
    report.append("| :--- | :--- | :---: | :---: |")
    per_year = df_results[df_results['type'] == 'Per-Year'].sort_values(['year', 'signal'])
    for _, r in per_year.iterrows():
        report.append(f"| {r['year']} | {r['signal']} | {r['correlation']:.4f} | {r['n']} |")

    report.append("\n## Interpretation")

    # Add auto-interpretation
    pooled_jan_mar = df_results[(df_results['signal'] == 'regime_signal_jan_mar') & (df_results['type'] == 'Pooled')]['correlation'].iloc[0]
    demeaned_jan_mar = df_results[(df_results['signal'] == 'regime_signal_jan_mar') & (df_results['type'] == 'Within-Year (Demeaned)')]['correlation'].iloc[0]

    if pooled_jan_mar > 0.4 and demeaned_jan_mar < 0.1:
        report.append("- **National Trend Dominance:** High pooled correlation but low within-year correlation indicates the signal mostly captures the common national trend (the tide), not local specificities (the waves).")
    elif demeaned_jan_mar > 0.2:
        report.append("- **Territorial Value:** Positive within-year correlation suggests the sectoral profile correctly maps national shocks to specific zones.")
    else:
        report.append("- **Weak Evidence:** Signal shows low correlation within years, suggesting limited forecasting power for local variance.")

    with open(output_report_path, 'w') as f:
        f.write("\n".join(report))

    print(f"Robust audit report saved to {output_report_path}")

if __name__ == "__main__":
    audit_robust_correlations()
