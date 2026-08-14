import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def generate_visualizations():
    try:
        df = pd.read_csv("batch_results.csv")
    except FileNotFoundError:
        print("batch_results.csv not found. Please run simulate.py first.")
        return

    # Calculate percentages
    df['crc_percent'] = (df['crc_detect'] / df['total_frames']) * 100
    df['checksum_percent'] = (df['checksum_detect'] / df['total_frames']) * 100
    df['crc_miss_rate'] = 100.0 - df['crc_percent']
    df['checksum_miss_rate'] = 100.0 - df['checksum_percent']

    # Pivot the CRC data to get Rows = Poly, Cols = Error Type
    crc_pivot = df.pivot(index='poly', columns='error_type', values='crc_percent')
    
    # For Checksum, it's independent of the poly, so we average it across polys
    checksum_avg = df.groupby('error_type')['checksum_percent'].mean()
    
    # Combine into one DataFrame for general Table
    final_table = crc_pivot.copy()
    final_table.loc['Checksum'] = checksum_avg
    
    # Reorder columns and rows
    col_order = ['single', 'two', 'odd', 'burst']
    final_table = final_table[col_order]
    row_order = ['CRC-8', 'CRC-10', 'CRC-16', 'CRC-32', 'Checksum']
    final_table = final_table.reindex(row_order)
    
    # ---------------------------------------------------------------------
    # 1. Summary Table Image (Existing)
    # ---------------------------------------------------------------------
    formatted_table = final_table.map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=formatted_table.values, 
                     rowLabels=formatted_table.index,
                     colLabels=formatted_table.columns, 
                     loc='center', 
                     cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    plt.title('Batch Aggregated Error Detection Rate (%)', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('batch_detection_table.png', dpi=300, bbox_inches='tight')
    plt.close()

    # ---------------------------------------------------------------------
    # 2. Heatmap of Detection Rates
    # ---------------------------------------------------------------------
    plt.figure(figsize=(8, 6))
    # We want a color map where 100 is green, and lower is red/orange.
    sns.heatmap(final_table, annot=True, fmt=".2f", cmap="RdYlGn", cbar_kws={'label': 'Detection Rate (%)'}, vmin=95, vmax=100)
    plt.title('Detection Reliability Heatmap', fontsize=16)
    plt.ylabel('Error Detection Method')
    plt.xlabel('Error Injection Type')
    plt.tight_layout()
    plt.savefig('heatmap_detection.png', dpi=300, bbox_inches='tight')
    plt.close()

    # ---------------------------------------------------------------------
    # 3. Bar Chart (Missed Error Rate for "two", "odd", and "burst" bits)
    # ---------------------------------------------------------------------
    miss_table = 100.0 - final_table
    
    plt.figure(figsize=(10, 6))
    x = np.arange(len(row_order))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width, miss_table['two'], width, label='Two-Bit Errors', color='coral')
    bars2 = ax.bar(x, miss_table['odd'], width, label='Odd Errors (1 or 3)', color='skyblue')
    bars3 = ax.bar(x + width, miss_table['burst'], width, label='Burst Errors', color='mediumpurple')
    
    ax.set_ylabel('False Negative Rate (Missed %) - Lower is Better')
    ax.set_title('Vulnerability to Specific Error Types (Missed Errors)')
    ax.set_xticks(x)
    ax.set_xticklabels(row_order)
    ax.legend()
    
    # Add values on top of bars
    for bar in bars1 + bars2 + bars3:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{height:.2f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig('missed_errors_bar.png', dpi=300, bbox_inches='tight')
    plt.close()

    # ---------------------------------------------------------------------
    # 4. Line Chart (Comparative Reliability Trend)
    # ---------------------------------------------------------------------
    plt.figure(figsize=(10, 6))
    
    for method in row_order:
        marker = 'o' if method == 'Checksum' else 's'
        linewidth = 3 if method == 'Checksum' else 2
        linestyle = '--' if method == 'Checksum' else '-'
        plt.plot(col_order, final_table.loc[method], marker=marker, linewidth=linewidth, linestyle=linestyle, label=method)

    plt.title('Reliability Trend Across Error Types', fontsize=16)
    plt.xlabel('Error Injection Type', fontsize=12)
    plt.ylabel('Detection Rate (%)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='lower left')
    plt.tight_layout()
    plt.savefig('comparative_reliability_line.png', dpi=300, bbox_inches='tight')
    plt.close()

    print("All visualizations generated successfully.")

if __name__ == "__main__":
    generate_visualizations()
