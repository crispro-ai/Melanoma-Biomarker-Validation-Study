#!/usr/bin/env python3
"""
Generate Publication-Quality Figures for GSE91061 IO Response Prediction
========================================================================

Generates all figures required for manuscript submission:
- Figure 1: System architecture (conceptual diagram)
- Figure 2: ROC curves (single pathways + composite)
- Figure 3: Boxplots (responders vs. non-responders)
- Figure 4: Feature importance (LR coefficients)
- Figure 5: 5-fold CV performance

Author: Zo
Date: January 28, 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import roc_curve, auc, roc_auc_score
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR.parent.parent / "scripts" / "data_acquisition" / "IO"
OUTPUT_DIR = BASE_DIR / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)

# Publication settings
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")
FIG_SIZE = (8, 6)
DPI = 300
FONT_SIZE = 12
TITLE_SIZE = 14

# Load data
print("Loading GSE91061 data...")
df = pd.read_csv(DATA_DIR / "gse91061_analysis_with_composites.csv")
pathway_stats = pd.read_csv(DATA_DIR / "gse91061_pathway_response_association.csv")
benchmark = pd.read_csv(DATA_DIR / "gse91061_benchmark_comparison.csv")

# Extract pathway columns and response
pathway_cols = ['TIL_INFILTRATION', 'T_EFFECTOR', 'ANGIOGENESIS', 'TGFB_RESISTANCE',
                'MYELOID_INFLAMMATION', 'PROLIFERATION', 'IMMUNOPROTEASOME', 'EXHAUSTION']
response = df['response'].values

print(f"Loaded {len(df)} samples ({response.sum()} responders, {len(response) - response.sum()} non-responders)")


# ============================================================================
# FIGURE 2: ROC CURVES (Single Pathways + Composite)
# ============================================================================

def generate_roc_curves():
    """Generate ROC curves for all pathways and composite models."""
    
    print("\nGenerating Figure 2: ROC Curves...")
    
    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=DPI)
    
    # Colors for pathways
    colors = plt.cm.tab10(np.linspace(0, 1, len(pathway_cols) + 3))
    
    # Plot single pathways
    for i, pathway in enumerate(pathway_cols):
        scores = df[pathway].values
        fpr, tpr, _ = roc_curve(response, scores)
        roc_auc = auc(fpr, tpr)
        
        # Get p-value from pathway_stats
        p_val = pathway_stats[pathway_stats['pathway'] == pathway]['p_value'].values[0]
        
        # Only label significant pathways
        label = f"{pathway} (AUC={roc_auc:.3f})" if p_val < 0.05 else None
        linestyle = '-' if p_val < 0.05 else '--'
        alpha = 0.8 if p_val < 0.05 else 0.4
        
        ax.plot(fpr, tpr, color=colors[i], linestyle=linestyle, alpha=alpha,
                linewidth=2, label=label)
    
    # Plot PD-L1 (baseline)
    pdl1_scores = df['PDL1_EXPRESSION'].values
    fpr_pdl1, tpr_pdl1, _ = roc_curve(response, pdl1_scores)
    roc_auc_pdl1 = auc(fpr_pdl1, tpr_pdl1)
    ax.plot(fpr_pdl1, tpr_pdl1, color='gray', linestyle=':', linewidth=2.5,
            label=f"PD-L1 (AUC={roc_auc_pdl1:.3f})", alpha=0.7)
    
    # Plot composite models
    # Weighted composite
    weighted_scores = df['composite_weighted'].values
    fpr_w, tpr_w, _ = roc_curve(response, weighted_scores)
    roc_auc_w = auc(fpr_w, tpr_w)
    ax.plot(fpr_w, tpr_w, color='red', linestyle='-', linewidth=3,
            label=f"Weighted Composite (AUC={roc_auc_w:.3f})", alpha=0.9)
    
    # Logistic regression composite
    lr_scores = df['composite_lr'].values
    fpr_lr, tpr_lr, _ = roc_curve(response, lr_scores)
    roc_auc_lr = auc(fpr_lr, tpr_lr)
    ax.plot(fpr_lr, tpr_lr, color='darkred', linestyle='-', linewidth=3.5,
            label=f"LR Composite (AUC={roc_auc_lr:.3f})", alpha=1.0)
    
    # Diagonal reference line
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.3, label='Random (AUC=0.50)')
    
    # Formatting
    ax.set_xlabel('False Positive Rate', fontsize=FONT_SIZE, fontweight='bold')
    ax.set_ylabel('True Positive Rate', fontsize=FONT_SIZE, fontweight='bold')
    ax.set_title('ROC Curves: Pathway-Based IO Response Prediction', 
                 fontsize=TITLE_SIZE, fontweight='bold', pad=15)
    ax.legend(loc='lower right', fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure2_roc_curves.png", dpi=DPI, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "figure2_roc_curves.pdf", bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'figure2_roc_curves.png'}")
    plt.close()


# ============================================================================
# FIGURE 3: BOXPLOTS (Responders vs. Non-Responders)
# ============================================================================

def generate_boxplots():
    """Generate boxplots comparing pathway scores between responders and non-responders."""
    
    print("\nGenerating Figure 3: Boxplots...")
    
    # Select top 4 pathways by AUC
    top_pathways = pathway_stats.nlargest(4, 'auc')['pathway'].tolist()
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=DPI)
    axes = axes.flatten()
    
    for idx, pathway in enumerate(top_pathways):
        ax = axes[idx]
        
        # Split by response
        resp_scores = df[df['response'] == 1][pathway].values
        nonresp_scores = df[df['response'] == 0][pathway].values
        
        # Boxplot
        bp = ax.boxplot([nonresp_scores, resp_scores], 
                       labels=['Non-Responders', 'Responders'],
                       patch_artist=True, widths=0.6)
        
        # Color boxes
        bp['boxes'][0].set_facecolor('#ffcccc')
        bp['boxes'][1].set_facecolor('#ccffcc')
        bp['boxes'][0].set_alpha(0.7)
        bp['boxes'][1].set_alpha(0.7)
        
        # Statistical test
        stat, p_val = stats.mannwhitneyu(nonresp_scores, resp_scores, alternative='two-sided')
        
        # Get AUC
        auc_val = pathway_stats[pathway_stats['pathway'] == pathway]['auc'].values[0]
        
        # Title with statistics
        title = f"{pathway}\nAUC={auc_val:.3f}, p={p_val:.4f}"
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_ylabel('Pathway Score (log2 TPM+1)', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add significance stars
        if p_val < 0.001:
            sig_text = '***'
        elif p_val < 0.01:
            sig_text = '**'
        elif p_val < 0.05:
            sig_text = '*'
        else:
            sig_text = 'ns'
        
        # Add significance bar
        y_max = max(np.max(resp_scores), np.max(nonresp_scores))
        y_pos = y_max * 1.1
        ax.plot([1, 2], [y_pos, y_pos], 'k-', linewidth=1.5)
        ax.text(1.5, y_pos * 1.05, sig_text, ha='center', fontsize=12, fontweight='bold')
    
    plt.suptitle('Pathway Scores: Responders vs. Non-Responders', 
                 fontsize=TITLE_SIZE, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure3_boxplots.png", dpi=DPI, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "figure3_boxplots.pdf", bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'figure3_boxplots.png'}")
    plt.close()


# ============================================================================
# FIGURE 4: FEATURE IMPORTANCE (LR Coefficients)
# ============================================================================

def generate_feature_importance():
    """Generate feature importance plot from logistic regression coefficients."""
    
    print("\nGenerating Figure 4: Feature Importance...")
    
    # Train LR model to get coefficients
    X = df[pathway_cols].values
    y = response
    
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X, y)
    
    # Get coefficients and intercept
    coefficients = lr.coef_[0]
    intercept = lr.intercept_[0]
    
    # Create DataFrame
    coef_df = pd.DataFrame({
        'pathway': pathway_cols,
        'coefficient': coefficients
    }).sort_values('coefficient', ascending=True)
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6), dpi=DPI)
    
    colors = ['red' if c < 0 else 'green' for c in coef_df['coefficient']]
    bars = ax.barh(coef_df['pathway'], coef_df['coefficient'], color=colors, alpha=0.7)
    
    # Add vertical line at zero
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    
    # Labels
    ax.set_xlabel('Logistic Regression Coefficient', fontsize=FONT_SIZE, fontweight='bold')
    ax.set_ylabel('Pathway', fontsize=FONT_SIZE, fontweight='bold')
    ax.set_title('Feature Importance: Logistic Regression Coefficients', 
                 fontsize=TITLE_SIZE, fontweight='bold', pad=15)
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, coef_df['coefficient'])):
        ax.text(val + (0.02 if val > 0 else -0.02), i, f'{val:.3f}',
                va='center', ha='left' if val > 0 else 'right', fontsize=9, fontweight='bold')
    
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure4_feature_importance.png", dpi=DPI, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "figure4_feature_importance.pdf", bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'figure4_feature_importance.png'}")
    plt.close()
    
    return coef_df


# ============================================================================
# FIGURE 5: 5-FOLD CV PERFORMANCE
# ============================================================================

def generate_cv_performance():
    """Generate 5-fold cross-validation performance plot."""
    
    print("\nGenerating Figure 5: 5-Fold CV Performance...")
    
    X = df[pathway_cols].values
    y = response
    
    # 5-fold CV
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    lr = LogisticRegression(max_iter=1000, random_state=42)
    
    cv_scores = cross_val_score(lr, X, y, cv=cv, scoring='roc_auc')
    
    # Plot
    fig, ax = plt.subplots(figsize=(8, 6), dpi=DPI)
    
    # Boxplot of CV scores
    bp = ax.boxplot([cv_scores], labels=['5-Fold CV'], patch_artist=True, widths=0.5)
    bp['boxes'][0].set_facecolor('#4CAF50')
    bp['boxes'][0].set_alpha(0.7)
    
    # Add individual fold scores as points
    for i, score in enumerate(cv_scores):
        ax.scatter([1], [score], color='darkgreen', s=100, zorder=3, alpha=0.7)
    
    # Add mean line
    mean_score = np.mean(cv_scores)
    std_score = np.std(cv_scores)
    ax.axhline(y=mean_score, color='red', linestyle='--', linewidth=2, 
               label=f'Mean: {mean_score:.3f} ± {std_score:.3f}')
    
    # Formatting
    ax.set_ylabel('AUC', fontsize=FONT_SIZE, fontweight='bold')
    ax.set_title('5-Fold Cross-Validation Performance', 
                 fontsize=TITLE_SIZE, fontweight='bold', pad=15)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim([0, 1])
    
    # Add text with statistics
    textstr = f'Mean AUC: {mean_score:.3f}\nStd: {std_score:.3f}\nMin: {np.min(cv_scores):.3f}\nMax: {np.max(cv_scores):.3f}'
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure5_cv_performance.png", dpi=DPI, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "figure5_cv_performance.pdf", bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'figure5_cv_performance.png'}")
    plt.close()
    
    return cv_scores


# ============================================================================
# FIGURE 1: SYSTEM ARCHITECTURE (Conceptual)
# ============================================================================

def generate_system_architecture():
    """Generate conceptual system architecture diagram."""
    
    print("\nGenerating Figure 1: System Architecture...")
    
    fig, ax = plt.subplots(figsize=(12, 8), dpi=DPI)
    ax.axis('off')
    
    # Define positions
    y_positions = [0.9, 0.7, 0.5, 0.3, 0.1]
    box_width = 0.15
    box_height = 0.08
    
    # Layer 1: Input
    input_box = plt.Rectangle((0.1, y_positions[0] - box_height/2), box_width, box_height,
                             facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(input_box)
    ax.text(0.175, y_positions[0], 'Pre-treatment\nRNA-seq', ha='center', va='center',
            fontsize=10, fontweight='bold')
    
    # Layer 2: Pathway Scoring
    pathway_box = plt.Rectangle((0.35, y_positions[1] - box_height/2), box_width*2, box_height,
                               facecolor='lightgreen', edgecolor='black', linewidth=2)
    ax.add_patch(pathway_box)
    ax.text(0.5, y_positions[1], '8 IO-Relevant Pathways\n(TIL, Effector, Exhaustion, etc.)',
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Layer 3: Composite Score
    composite_box = plt.Rectangle((0.7, y_positions[2] - box_height/2), box_width*1.5, box_height,
                                 facecolor='lightyellow', edgecolor='black', linewidth=2)
    ax.add_patch(composite_box)
    ax.text(0.85, y_positions[2], 'Logistic Regression\nComposite Score',
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Layer 4: Prediction
    pred_box = plt.Rectangle((0.35, y_positions[3] - box_height/2), box_width*2, box_height,
                            facecolor='lightcoral', edgecolor='black', linewidth=2)
    ax.add_patch(pred_box)
    ax.text(0.5, y_positions[3], 'IO Response Prediction\n(AUC = 0.780)',
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Layer 5: Clinical Decision
    clinical_box = plt.Rectangle((0.1, y_positions[4] - box_height/2), box_width*3, box_height,
                                facecolor='lightpink', edgecolor='black', linewidth=2)
    ax.add_patch(clinical_box)
    ax.text(0.35, y_positions[4], 'Clinical Decision Support\n(Responder vs. Non-Responder)',
            ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Arrows
    arrow_props = dict(arrowstyle='->', lw=2, color='black')
    ax.annotate('', xy=(0.25, y_positions[0] - 0.05), xytext=(0.4, y_positions[1] + 0.05),
                arrowprops=arrow_props)
    ax.annotate('', xy=(0.6, y_positions[1] - 0.05), xytext=(0.75, y_positions[2] + 0.05),
                arrowprops=arrow_props)
    ax.annotate('', xy=(0.925, y_positions[2] - 0.05), xytext=(0.6, y_positions[3] + 0.05),
                arrowprops=arrow_props)
    ax.annotate('', xy=(0.5, y_positions[3] - 0.05), xytext=(0.35, y_positions[4] + 0.05),
                arrowprops=arrow_props)
    
    ax.set_title('System Architecture: Pathway-Based IO Response Prediction', 
                 fontsize=TITLE_SIZE, fontweight='bold', pad=20)
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "figure1_system_architecture.png", dpi=DPI, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / "figure1_system_architecture.pdf", bbox_inches='tight')
    print(f"✅ Saved: {OUTPUT_DIR / 'figure1_system_architecture.png'}")
    plt.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GENERATING PUBLICATION-QUALITY FIGURES FOR GSE91061")
    print("=" * 70)
    
    # Generate all figures
    generate_system_architecture()
    generate_roc_curves()
    generate_boxplots()
    coef_df = generate_feature_importance()
    cv_scores = generate_cv_performance()
    
    print("\n" + "=" * 70)
    print("✅ ALL FIGURES GENERATED SUCCESSFULLY")
    print("=" * 70)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nGenerated files:")
    print("  - figure1_system_architecture.png/pdf")
    print("  - figure2_roc_curves.png/pdf")
    print("  - figure3_boxplots.png/pdf")
    print("  - figure4_feature_importance.png/pdf")
    print("  - figure5_cv_performance.png/pdf")
    
    # Save coefficient data
    coef_df.to_csv(OUTPUT_DIR / "lr_coefficients.csv", index=False)
    print(f"\n✅ Saved LR coefficients: {OUTPUT_DIR / 'lr_coefficients.csv'}")
    
    # Save CV statistics
    cv_stats = pd.DataFrame({
        'fold': range(1, 6),
        'auc': cv_scores
    })
    cv_stats.to_csv(OUTPUT_DIR / "cv_statistics.csv", index=False)
    print(f"✅ Saved CV statistics: {OUTPUT_DIR / 'cv_statistics.csv'}")
