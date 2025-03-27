import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import numpy as np


def plot_histgram(data: np.ndarray):
    if 1 < len(data.shape):
        data = data.flatten()
    data = data[~np.isnan(data)]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title("Distribution", fontsize=17)
    ax.set_xlabel("Value", fontsize=15)
    ax.set_ylabel("Frequency", fontsize=15)
    color = "#008899"
    ax.hist(data, bins=20, fc=to_rgba(color, 0.5), ec=color, density=True)

    q1 = np.nanquantile(data, 0.25)
    q3 = np.nanquantile(data, 0.75)
    iqr = q3 - q1
    upper_func = lambda x: q3 + x * iqr
    lower_func = lambda x: q1 - x * iqr
    lc = "black"
    ax.axvline(upper_func(1.5), c=lc, ls="--", lw=2, label="iqr * 1.5")
    ax.axvline(lower_func(1.5), c=lc, ls="--", lw=2)
    ax.axvline(upper_func(2.5), c=lc, ls="-.", lw=2, label="iqr * 2.5")
    ax.axvline(lower_func(2.5), c=lc, ls="-.", lw=2)
    ax.axvline(upper_func(3.5), c=lc, ls=":", lw=2, label="iqr * 3.5")
    ax.axvline(lower_func(3.5), c=lc, ls=":", lw=2)
    legend = plt.legend(loc="upper right")
    legend.get_frame().set_alpha(1)
    plt.show()
