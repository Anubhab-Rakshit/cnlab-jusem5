import pandas as pd
import matplotlib.pyplot as plt
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

    # Pivot the CRC data to get Rows = Poly, Cols = Error Type
    crc_pivot = df.pivot(index='poly', columns='error_type', values='crc_percent')
    
    # For Checksum, it's independent of the poly, so we can just average it across polys for each error type
    checksum_avg = df.groupby('error_type')['checksum_percent'].mean()
    
    # Combine into one DataFrame
    final_table = crc_pivot.copy()
    final_table.loc['Checksum'] = checksum_avg
    
    # Reorder columns to a logical order
    col_order = ['single', 'two', 'odd', 'burst']
    final_table = final_table[col_order]
    
    # Reorder rows to a logical order
    row_order = ['CRC-8', 'CRC-10', 'CRC-16', 'CRC-32', 'Checksum']
    final_table = final_table.reindex(row_order)
    
    # Format as percentages
    formatted_table = final_table.map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    print("Batch Aggregated Detection Rates:")
    print(formatted_table)
    
    # Plot as a visual table
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('tight')
    ax.axis('off')
    
    # Add column names and row names to the table data
    cell_text = formatted_table.values
    row_labels = formatted_table.index
    col_labels = formatted_table.columns
    
    table = ax.table(cellText=cell_text, 
                     rowLabels=row_labels,
                     colLabels=col_labels, 
                     loc='center', 
                     cellLoc='center')
                     
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    
    plt.title('Batch Aggregated Error Detection Rate (%)', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('batch_detection_table.png', dpi=300, bbox_inches='tight')
    print("Saved batch_detection_table.png")

if __name__ == "__main__":
    generate_visualizations()
