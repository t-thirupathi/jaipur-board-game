from agent_jaipur import *
import pickle

state_values = dict()

def load_values():
    global state_values
    try:
        f = open('state_values.pickle', 'rb')
        state_values = pickle.load(f)
    except:
        pass


load_values()

print(len(state_values))

count = 0
for i in state_values:
    if state_values[i] != 0:
        count += 1
        
    # if state_values[i] not in (-0.5, 0, 0.5):
    #     print(i, state_values[i])

print(count)

for i in sorted(state_values, key=state_values.get)[:20]:
    print(i, state_values[i])
print()

for i in sorted(state_values, key=state_values.get)[-20:]:
    print(i, state_values[i])
            


