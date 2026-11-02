
for i in range(0,255):
    color = f"\033[38;5;33;48;5;{str(i)}m"
    print(f"\t{color}{str(i).center(7)}\033[0m",end = "", flush = True)
    if(i%10 == 0 and i!=1):
        print("\n",end = "", flush = True)