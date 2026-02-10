import numpy as np

def calculate_s_curve(total_budget, duration_months):
    """Very simple placeholder S-curve – will improve later"""
    if duration_months <= 0:
        return []
    
    time_percent = np.linspace(0, 1, int(duration_months) + 1)
    # Very basic logistic approximation
    k = 8.0
    midpoint = 0.55
    cash_percent = 1 / (1 + np.exp(-k * (time_percent - midpoint)))
    cash_percent = cash_percent / cash_percent[-1]  # normalize
    
    monthly_spend = np.diff(cash_percent, prepend=0) * total_budget
    return monthly_spend.tolist()

# Test
if __name__ == "__main__":
    print(calculate_s_curve(100000000, 24))
