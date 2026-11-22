values = open("block.ptrace").read().splitlines()[1].split()
print("count=", len(values))
print("first 20:", values[:20])
print("unique values:", sorted(set(values), key=float))
