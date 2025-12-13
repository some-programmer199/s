import random
import tqdm

def battle(va):
    rand_a= random.random()
    rand_b= random.random()
    if rand_a >= rand_b:
        rand_b= random.random()

    if rand_a > rand_b:
        return (1,0)
    else :
        return (0,1)

score= [0,0]
va= 0.5
gradienta= 0.000001
lr= 0.0001
eps= 0.000001
for i in tqdm.tqdm(range(int(10e6))):
    result= battle(va)
    score[0] += result[0]
    score[1] += result[1]
    lossa= - (score[1] - score[0]) / (score[0] + score[1])
    lossb= - (score[0] - score[1]) / (score[0] + score[1])
    gradienta = (score[1] - score[0]) / (score[0] + score[1] + eps)
    va -= lr*gradienta
    va = max(0.0, min(1.0, va))
    
    lr *= 0.999
    
print("Final Score: Player A - {}, Player B - {}".format(score[0], score[1]))
print("Final Value for Player A: {:.6f}".format(va))
