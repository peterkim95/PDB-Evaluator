import sys

"""
	Usage: 
	> python generate_table.py <VAR_CAP> <VAL_CAP>

	Generates a table with all row probabilities = 0.5
"""

def create_table(var_cap, val_cap, curr_list):
    if len(curr_list) == var_cap:
        print(','.join(str(x) for x in curr_list) + ",0.5")
        return
    for v in range(val_cap):
        next_list = curr_list[:]
        next_list.append(v)
        create_table(var_cap, val_cap, next_list)

def main():
    create_table(int(sys.argv[1]), int(sys.argv[2]), [])

if __name__ == "__main__":
	main()