import lift
import time

"""
	Quick script to see the speedup on our small test case
	With my code: Avg run time = 0.00095
	Original: Avg run time = 0.00123

	On new larger test case (using T4)
	With my code: Avg run time = 0.00409
	Original: Avg run time = 0.133
"""

def main():
	avg_base_time = 0
	for i in range(100):
	    time_start = time.time()
	    lift.main()
	    time_end = time.time()
	    avg_base_time += time_end - time_start
	print("Avg run time: ", avg_base_time / 1000)

if __name__ == '__main__':
	main()