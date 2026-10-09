import numpy as np
import matplotlib.pyplot as plt

def generate_walsh(n):
    if n == 1:
        return np.array([[1]])
    half = generate_walsh(n // 2)
    return np.vstack((np.hstack((half, half)), np.hstack((half, -half))))

def plot_cdma_signals():
    # Setup
    N = 4 # Walsh size
    walsh_matrix = generate_walsh(N)
    
    # 1. Data Generation (e.g. 4 bits per station)
    data_bits = {
        0: np.array([1, 0, 1, 1]), # Station 0 data
        1: np.array([0, 1, 0, 0]), # Station 1 data
        2: np.array([1, 1, 0, 1]), # Station 2 data
        3: np.array([0, 0, 1, 0])  # Station 3 data
    }
    
    # 2. Polar Encoding (0 -> -1, 1 -> 1)
    polar_data = {i: np.where(bits == 0, -1, 1) for i, bits in data_bits.items()}
    
    # 3. Spread Spectrum (Kronecker product with Walsh Code)
    chips = {i: np.kron(polar_data[i], walsh_matrix[i]) for i in range(N)}
    
    # 4. Superposition (The physical wire)
    summed_signal = np.sum([chips[i] for i in range(N)], axis=0)
    
    # 5. Adding AWGN Noise
    noise_sigma = 0.5
    noisy_signal = summed_signal + np.random.normal(0, noise_sigma, summed_signal.shape)
    
    # 6. Plotting
    fig, axs = plt.subplots(6, 1, figsize=(12, 12), sharex=True)
    fig.suptitle('CDMA Signal Processing: Encoding, Superposition, and Noise', fontsize=16, fontweight='bold')
    
    time_axis = np.arange(len(summed_signal))
    
    # Plot Station 0 Transmitted Chips
    axs[0].step(time_axis, chips[0], where='mid', color='blue', linewidth=2)
    axs[0].set_title('Station 0 Transmitted Chips (Data: 1 0 1 1)', loc='left')
    axs[0].set_ylabel('Amplitude')
    axs[0].grid(True, linestyle='--', alpha=0.7)
    
    # Plot Station 1 Transmitted Chips
    axs[1].step(time_axis, chips[1], where='mid', color='green', linewidth=2)
    axs[1].set_title('Station 1 Transmitted Chips (Data: 0 1 0 0)', loc='left')
    axs[1].set_ylabel('Amplitude')
    axs[1].grid(True, linestyle='--', alpha=0.7)
    
    # Plot Summed Signal (No Noise)
    axs[2].step(time_axis, summed_signal, where='mid', color='purple', linewidth=2)
    axs[2].set_title('Superimposed Signal on the Wire (All 4 Stations Added)', loc='left')
    axs[2].set_ylabel('Amplitude')
    axs[2].grid(True, linestyle='--', alpha=0.7)
    
    # Plot Noisy Signal
    axs[3].step(time_axis, noisy_signal, where='mid', color='red', linewidth=2)
    axs[3].set_title(f'Signal corrupted by AWGN Noise (Sigma = {noise_sigma})', loc='left')
    axs[3].set_ylabel('Amplitude')
    axs[3].grid(True, linestyle='--', alpha=0.7)
    
    # Decoding Station 0 from Noisy Signal
    reshaped_noisy = noisy_signal.reshape(-1, N)
    decoded_st0 = np.dot(reshaped_noisy, walsh_matrix[0]) / N
    
    # Decoding Station 1 from Noisy Signal
    decoded_st1 = np.dot(reshaped_noisy, walsh_matrix[1]) / N
    
    axs[4].stem(np.arange(len(decoded_st0)), decoded_st0, linefmt='b-', markerfmt='bo', basefmt='k-')
    axs[4].axhline(y=0, color='k', linestyle='-')
    axs[4].set_title('Station 0 Decoder Output (Dot Product result)', loc='left')
    axs[4].set_ylabel('Value')
    axs[4].grid(True, linestyle='--', alpha=0.7)
    
    axs[5].stem(np.arange(len(decoded_st1)), decoded_st1, linefmt='g-', markerfmt='go', basefmt='k-')
    axs[5].axhline(y=0, color='k', linestyle='-')
    axs[5].set_title('Station 1 Decoder Output (Dot Product result)', loc='left')
    axs[5].set_ylabel('Value')
    axs[5].set_xlabel('Time (Bits)')
    axs[5].grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig('cdma_signals.png', dpi=300, bbox_inches='tight')
    print("Saved CDMA visualization to cdma_signals.png")

if __name__ == "__main__":
    plot_cdma_signals()
