class Node:
    def __init__(self,seq,value):
        self.value = value
        self.seq = seq.append(value)
        self.children = []
        if not self._test_seq(self):
            self.pruned=True
        else:
            self.pruned=False
    def _test_seq(self):
        for i in range(len(self.seq)-1):
            for j in range(len(self.seq)-1):
                if i+j==self.value[1] and i==self.value[0] and j==self.value[0]:
                    return True
        return False
    def expand(self):
        for i in range(1,4):
            child=Node(self.seq,(i,self.value[1]+1))
            if not child.pruned:
                self.children.append(child)
root=Node([],(1,1))
valid_sequences=[]
def search(depth=13,root=root):
    #searches for a valid sequence of given depth
    if depth==0:
        valid_sequences.append(root.seq)
        return
    root.expand()
    for child in root.children:
        search(depth-1,child)
search()
    