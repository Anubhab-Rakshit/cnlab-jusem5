import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Set modern publication styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica', 'Arial', 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

def generate_visualizations():
    csv_file = "batch_results.csv"
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found. Please run simulate.py first.")
        return
        
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} simulation records from {csv_file}")
    
    # -------------------------------------------------------------------------
    # 1. Multi-Bar Chart: Throughput Across Protocols & Channel Conditions
    # -------------------------------------------------------------------------
    plt.figure(figsize=(11, 6))
    
    # Group by key scenarios
    target_scenarios = [
        ("SAW_Ideal", "Stop-and-Wait (Ideal)"),
        ("SAW_Loss05", "Stop-and-Wait (5% Loss)"),
        ("SAW_Loss15", "Stop-and-Wait (15% Loss)"),
        ("GBN_W4_Ideal", "GBN W=4 (Ideal)"),
        ("GBN_W4_Loss05", "GBN W=4 (5% Loss)"),
        ("GBN_W4_Loss15", "GBN W=4 (15% Loss)"),
        ("SR_W4_Ideal", "SR W=4 (Ideal)"),
        ("SR_W4_Loss05", "SR W=4 (5% Loss)"),
        ("SR_W4_Loss15", "SR W=4 (15% Loss)"),
    ]
    
    scen_keys = [s[0] for s in target_scenarios]
    scen_labels = [s[1] for s in target_scenarios]
    
    subset = df[df['scenario_label'].isin(scen_keys)]
    grouped = subset.groupby('scenario_label')['throughput_kbps'].mean().reindex(scen_keys)
    
    colors = [
        '#3498db', '#5dade2', '#85c1e9', # SAW shades
        '#e67e22', '#eb984e', '#f0b27a', # GBN shades
        '#2ecc71', '#58d68d', '#82e0aa'  # SR shades
    ]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(range(len(grouped)), grouped.values, color=colors, width=0.65, edgecolor='#2c3e50', linewidth=0.8)
    
    ax.set_xticks(range(len(grouped)))
    ax.set_xticklabels(scen_labels, rotation=35, ha='right', fontsize=10, fontweight='medium')
    ax.set_ylabel('Average Throughput (KB/s)', fontsize=12, fontweight='bold')
    ax.set_title('Flow Control Throughput Comparison Across Protocols & Loss Rates', fontsize=15, pad=15, fontweight='bold')
    
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f'{h:.2f} KB/s',
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
                    
    plt.tight_layout()
    plt.savefig('throughput_comparison_bar.png', dpi=300)
    plt.close()
    print("[1/5] Generated throughput_comparison_bar.png")
    
    # -------------------------------------------------------------------------
    # 2. Pie Charts: Transmission Breakdown & Retransmission Waste (15% Loss)
    # -------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    pie_scenarios = [
        ("SAW_Loss15", "Stop-and-Wait (15% Loss)", axes[0]),
        ("GBN_W4_Loss15", "Go-Back-N W=4 (15% Loss)", axes[1]),
        ("SR_W4_Loss15", "Selective Repeat W=4 (15% Loss)", axes[2]),
    ]
    
    for scen, title, ax in pie_scenarios:
        scen_df = df[df['scenario_label'] == scen]
        total_useful = scen_df['total_frames'].sum()
        total_retrans = scen_df['retransmissions'].sum()
        
        sizes = [total_useful, total_retrans]
        labels = ['Useful Frames', 'Retransmissions']
        pie_colors = ['#27ae60', '#e74c3c']
        explode = (0, 0.08)
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            explode=explode,
            labels=labels,
            autopct='%1.1f%%',
            startangle=140,
            colors=pie_colors,
            textprops=dict(color="black", fontweight='bold'),
            wedgeprops=dict(edgecolor="#ffffff", linewidth=1.5)
        )
        ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
        
    plt.suptitle("Retransmission Overhead & Protocol Efficiency under 15% Channel Loss", fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('efficiency_piechart.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[2/5] Generated efficiency_piechart.png")
    
    # -------------------------------------------------------------------------
    # 3. Histogram: Completion Time / Latency Distribution across 50 Files
    # -------------------------------------------------------------------------
    plt.figure(figsize=(11, 6))
    
    saw_times = df[df['scenario_label'] == 'SAW_Loss05']['elapsed_sec']
    gbn_times = df[df['scenario_label'] == 'GBN_W4_Loss05']['elapsed_sec']
    sr_times = df[df['scenario_label'] == 'SR_W4_Loss05']['elapsed_sec']
    
    bins = np.linspace(0, max(saw_times.max(), gbn_times.max(), sr_times.max()) * 1.1, 20)
    
    plt.hist(saw_times, bins=bins, alpha=0.6, label='Stop-and-Wait', color='#e74c3c', edgecolor='black')
    plt.hist(gbn_times, bins=bins, alpha=0.6, label='Go-Back-N (W=4)', color='#f39c12', edgecolor='black')
    plt.hist(sr_times, bins=bins, alpha=0.6, label='Selective Repeat (W=4)', color='#2ecc71', edgecolor='black')
    
    plt.title('Transmission Latency Distribution Across 50 Test Files (5% Loss)', fontsize=15, fontweight='bold', pad=15)
    plt.xlabel('Elapsed Time per File Transfer (Seconds)', fontsize=12, fontweight='bold')
    plt.ylabel('File Count (Frequency)', fontsize=12, fontweight='bold')
    plt.legend(loc='upper right', frameon=True, fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig('delay_distribution_hist.png', dpi=300)
    plt.close()
    print("[3/5] Generated delay_distribution_hist.png")
    
    # -------------------------------------------------------------------------
    # 4. Line Chart: Throughput Scaling with Window Size
    # -------------------------------------------------------------------------
    plt.figure(figsize=(10, 6))
    
    # Ideal line
    gbn_w = [1, 4, 8]
    gbn_ideal_tp = [
        df[df['scenario_label'] == 'SAW_Ideal']['throughput_kbps'].mean(),
        df[df['scenario_label'] == 'GBN_W4_Ideal']['throughput_kbps'].mean(),
        df[df['scenario_label'] == 'GBN_W8_Ideal']['throughput_kbps'].mean(),
    ]
    sr_ideal_tp = [
        df[df['scenario_label'] == 'SAW_Ideal']['throughput_kbps'].mean(),
        df[df['scenario_label'] == 'SR_W4_Ideal']['throughput_kbps'].mean(),
        df[df['scenario_label'] == 'SR_W8_Ideal']['throughput_kbps'].mean(),
    ]
    
    plt.plot(gbn_w, gbn_ideal_tp, marker='o', linewidth=2.5, markersize=8, color='#e67e22', label='Go-Back-N (Ideal Channel)')
    plt.plot(gbn_w, sr_ideal_tp, marker='s', linewidth=2.5, markersize=8, color='#27ae60', linestyle='--', label='Selective Repeat (Ideal Channel)')
    
    plt.title('Throughput Scaling with Window Size (W=1, 4, 8)', fontsize=15, fontweight='bold', pad=15)
    plt.xlabel('Sliding Window Size (Frames)', fontsize=12, fontweight='bold')
    plt.ylabel('Throughput (KB/s)', fontsize=12, fontweight='bold')
    plt.xticks([1, 4, 8], ['W=1 (SAW)', 'W=4', 'W=8'])
    plt.legend(loc='lower right', fontsize=11, frameon=True)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig('window_scaling_line.png', dpi=300)
    plt.close()
    print("[4/5] Generated window_scaling_line.png")
    
    # -------------------------------------------------------------------------
    # 5. Summary Table Image: Publication-ready Metrics Table
    # -------------------------------------------------------------------------
    summary_scenarios = [
        ("SAW_Ideal", "Stop-and-Wait", 1, "0.0%"),
        ("SAW_Loss15", "Stop-and-Wait", 1, "15.0%"),
        ("GBN_W4_Ideal", "Go-Back-N", 4, "0.0%"),
        ("GBN_W4_Loss15", "Go-Back-N", 4, "15.0%"),
        ("GBN_W8_Ideal", "Go-Back-N", 8, "0.0%"),
        ("SR_W4_Ideal", "Selective Repeat", 4, "0.0%"),
        ("SR_W4_Loss15", "Selective Repeat", 4, "15.0%"),
        ("SR_W8_Ideal", "Selective Repeat", 8, "0.0%"),
        ("SAW_DropInject", "SAW (Drop Injected)", 1, "Forced Drop"),
        ("GBN_DropInject", "GBN (Drop Injected)", 4, "Forced Drop"),
        ("SR_CorrInject", "SR (Corr Injected)", 4, "Forced Corr"),
    ]
    
    rows = []
    for scen, proto_name, win, loss_lbl in summary_scenarios:
        scen_df = df[df['scenario_label'] == scen]
        if len(scen_df) == 0:
            continue
        avg_tp = f"{scen_df['throughput_kbps'].mean():.2f} KB/s"
        avg_lat = f"{scen_df['elapsed_sec'].mean():.3f} s"
        avg_eff = f"{scen_df['efficiency_percent'].mean():.1f}%"
        integrity = f"{(scen_df['integrity_pass'].mean() * 100):.1f}%"
        
        rows.append([proto_name, win, loss_lbl, avg_tp, avg_lat, avg_eff, integrity])
        
    columns = ["Protocol", "Window", "Loss Rate", "Avg Throughput", "Avg Latency", "Efficiency", "Integrity Match"]
    
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.axis('tight')
    ax.axis('off')
    
    tbl = ax.table(
        cellText=rows,
        colLabels=columns,
        loc='center',
        cellLoc='center'
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.2, 1.8)
    
    # Style table headers
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#2c3e50')
        elif row % 2 == 0:
            cell.set_facecolor('#f2f4f4')
            
    plt.title('Batch Simulation Aggregated Performance Summary (50 Files)', fontsize=15, pad=20, fontweight='bold')
    plt.tight_layout()
    plt.savefig('batch_summary_table.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("[5/5] Generated batch_summary_table.png")
    
    print("\nAll 5 charts generated successfully!")

if __name__ == "__main__":
    generate_visualizations()
