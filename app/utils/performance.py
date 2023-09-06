import numpy as np


# 最大回撤
def maxdrawdown(arr: np.array):
    i = np.argmax((np.maximum.accumulate(arr) - arr) / np.maximum.accumulate(arr))  # end of the period
    j = np.argmax(arr[:i])  # start of period 最大值
    return 1 - arr[i] / arr[j]
