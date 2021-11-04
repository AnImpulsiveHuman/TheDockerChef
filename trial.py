import os
import json

file = "dictdemo"

#c = {"tools":"locate,dnsutils","name":"sensible-bulldog","day":"Monday"}

#json.dump(c, open(file,'w'))

#d = json.load(open(file))

#for i in d:
#    print("Key: " + i)

path = "hello"

ans1 = file+path
ans2 = path+file

print(ans1)
print(ans2)