import pandas as pd
import matplotlib.pyplot as plt
import os

def main():
    if not os.path.exists("results.csv"):
        print("Error: results.csv not found. Run simulate.py first.")
        return
        
    df = pd.read_csv("results.csv")
    
    # 1. p-persistent CSMA vs p (for fixed N=10)
    df_p = df[(df['strategy'] == 'p-persistent') & (df['N'] == 10)].copy()
    if not df_p.empty:
        df_p = df_p.sort_values(by='p')
        
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.plot(df_p['p'], df_p['collisions'], marker='o', color='red')
        plt.title('Collisions vs p')
        plt.xlabel('Probability (p)')
        plt.ylabel('Collisions')
        plt.grid(True)
        
        plt.subplot(1, 3, 2)
        plt.plot(df_p['p'], df_p['avg_delay'], marker='o', color='blue')
        plt.title('Transmission Delay vs p')
        plt.xlabel('Probability (p)')
        plt.ylabel('Delay (s)')
        plt.grid(True)
        
        plt.subplot(1, 3, 3)
        plt.plot(df_p['p'], df_p['throughput'], marker='o', color='green')
        plt.title('Efficiency vs p')
        plt.xlabel('Probability (p)')
        plt.ylabel('Efficiency (frames/s)')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('p_persistent_vs_p.png')
        print("Saved p_persistent_vs_p.png")
        plt.close()
        
    # 2. All schemes vs N
    schemes = ["non-persistent", "1-persistent", "p-persistent", "csmacd"]
    metrics = ['collisions', 'avg_delay', 'throughput']
    titles = ['Collisions vs N', 'Avg Transmission Delay vs N', 'Efficiency vs N']
    ylabels = ['Collisions', 'Delay (s)', 'Efficiency (frames/s)']
    
    plt.figure(figsize=(15, 5))
    
    for i, metric in enumerate(metrics):
        plt.subplot(1, 3, i+1)
        for strategy in schemes:
            # For p-persistent, we want to make sure we only grab the one that was run for varying N (using best_p)
            df_strat = df[(df['strategy'] == strategy)].copy()
            # If a strategy has multiple p's for the same N (e.g. p-persistent), we only want the ones where it was part of the varying N phase.
            # To distinguish, we can group by N and take the mean, or just trust the dataframe structure.
            df_strat = df_strat.groupby('N')[['collisions', 'avg_delay', 'throughput']].mean().reset_index()
            
            plt.plot(df_strat['N'], df_strat[metric], marker='o', label=strategy)
            
        plt.title(titles[i])
        plt.xlabel('Number of Stations (N)')
        plt.ylabel(ylabels[i])
        plt.legend()
        plt.grid(True)
        
    plt.tight_layout()
    plt.savefig('schemes_vs_N.png')
    print("Saved schemes_vs_N.png")
    plt.close()

if __name__ == "__main__":
    main()
