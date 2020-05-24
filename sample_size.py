from math import ceil
import numpy as np
from scipy.stats import norm

""" Credits to Evan Miller, all I did was reimplement this in Python. """


def sample_size(alpha, power, baseline, delta):
    if baseline > 0.5:
        baseline = 1.0 - baseline

    t_alpha2 = norm.ppf(1.0 - alpha / 2)
    t_beta = norm.ppf(power)

    sd1 = np.sqrt(2 * baseline * (1 - baseline))
    sd2 = np.sqrt(
        baseline * (1 - baseline) + (baseline + delta) * (1 - baseline - delta)
    )

    return ceil((t_alpha2 * sd1 + t_beta * sd2) ** 2 / delta ** 2)
