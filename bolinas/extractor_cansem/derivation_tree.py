import sys
import re
from sets import Set
from Queue import Queue
from collections import defaultdict

from bolinas.lib.amr.amr import Dag
from data_structures import RuleInstance, CanonicalDerivation, Edge
from data_structures import tibFormat, galFormat


class DerivationTree(object):
    """
    Simple binary tree class
    Variables:
    parent, children (Tree elements or None)
    label (associated label: AMRtriple)
    rule  (name of the rule associated with generating its children)
    dRule (derivRule attached to this particular node)
    """

    def __init__(self):
        self.parent = None      # DerivationTree
        self.children = []      # [DerivationTree]
        self.label = None       # AMR tuple (parent, edge, child) ~~ Node of the Canonical Derivation Tree
        self.rule = None        # Canonical Rule ~~ Edge of the Canonical Derivation Tree
        self.align = None
    
    def __str__(self):
        return "Node: " + str(self.label) + "\n" \
                + "Rule: " + str(self.rule) + "\n" \
    
    @classmethod
    def makeRecursiveNode(cls,parent,label,rules):
        """
        Given a parent node (parent), a label (AMRtriple) and a set of RuleInstances
        generate a node (recurvisely) and return itself
        """
        if label == None:   return None

        node = None 
        # label = triple to start with. Find rule:
        for i in xrange(len(rules)):
            if label == rules[i].fromAT:
                # This matches our rule!

                subrules = rules[(i+1):]
                rule = rules[i]
                node = cls()
                
                for toAT in rule.toATs:
                    node.children.append(cls.makeRecursiveNode(node,toAT,subrules))

                node.parent = parent
                node.label  = label
                node.rule   = rule.ruleType
                node.align  = label[1].align
                #node.tags   = label.tags

                return node

        if node == None: # Didn't find any rule with this node as parent --> Leaf node
            if label == None:
                print "This shouldn't happen"
            node = cls()
            node.parent = parent
            node.label  = label
            node.rule   = "Instance"
            node.align  = label[1].align
            #node.tags   = label.tags
            return node

    def getDag(self):
        triples = self.recDag([])
        return Dag.from_triples(triples,[self])

    def recDag(self,triples):
        for child in self.children:
            triples.append((self,self.rule,child))
            triples = child.recDag(triples)
        return triples

    def getTiburonTree(self):
        """
        Gets the derviation tree in depth first order and prints it in Tiburon format
        """    

        def combiner(par, childmap, depth):
            """
            Takes parent and list of children to combine
            """
            rule = childmap.keys()[0]
            string = "%s( %s )" % ("%s_%s"%(par,rule), " ".join(["%s"%(v) for v in childmap.values()]))
            return string

        def extractor(node,firsthit,leaf):
            """
            Returns node representation
            """
            if leaf:    return tibFormat(node.label[1][0]).lower() #.replace('"','')
            #if leaf:    return tibFormat(node.label[1][1] + "(" + node.label[2] + ")")
            else:       return tibFormat(node.label[1][0])

        def hedge_combiner(something):
            return something[0]

        tree = self.getDag()
        return tree.dfs(combiner = combiner, extractor = extractor, hedge_combiner = hedge_combiner)[0]
        #return "ROOT( " + tree.dfs(combiner = combiner, extractor = extractor, hedge_combiner = hedge_combiner)[0] + " )"

    @classmethod
    def fromDerivation(cls,cd):
        """
        Takes a canonical derivation and builds a derivation tree
        """
        root = cls.makeRecursiveNode(None,cd.rules[0].fromAT,cd.rules)
        return root

    """
    def getTriples(self, alignments = False):
        '''
        Recursively returns all triples contained in the subtree rooted at a given node.
        Triples are all rules creating the subgraph, not including alignment edges
        '''
        
        (a,b,c) = self.label.get()
        if not self.label.isNonterminal():
            label = (a + str(b),'.'.join(map(str,self.span)),'.'.join(map(str,self.cSpan)))
        else:
            label = (a + str(b) + c, '.'.join(map(str,self.span)), '.'.join(map(str,self.cSpan)))


        (x,y,z) = label
        if self.frontier: label = (x,y,z+ " FRONTIER")
        triples = []

        for c in self.children:
            (childTrip,childLabel) = c.getTriples(alignments)
            triples.append((label,self.rule,childLabel))
            triples += childTrip

        if alignments:
            for word in self.align:
                triples.append((label,"align",word))

        return (triples,label)
    """

    def getGHKMtriple_Java(self):
        '''
        Returns a triple of strings (ptb,a,f) formatted for use by Galley's GHKM implementation in Java
        '''
        global magicCount
        magicCount = 0

        def combiner(par, childmap, depth):
            ''' 
            Takes parent and list of children to combine
            '''
            rule = childmap.keys()[0]
            state = par[2]

            if len(childmap) == 1 and childmap.values()[0][2] == "child":
                string = "(%s %s)" % ("%s@%s@%s"%(galFormat(par[0]),rule,state), " ".join(["%s"%(v) for (v,a,t) in childmap.values()]))
            else:
                string = "(%s %s)" % ("%s@%s@%s"%(galFormat(par[0]),rule,state), " ".join(["%s"%(v) for (v,a,t) in childmap.values()]))

            align = [item for (v,a,t) in childmap.values() for item in a] + par[1]


            return (string,align,par[2])

        def extractor(node,firsthit,leaf):
            '''
            Returns node representation
            '''
            global magicCount
            if leaf:
                # Alignment magic: boy-2 -> int(2), combine this with the magicCount (for lack of a better name)
                alignments = ["%d-%d"%(magicCount,int(align)) for align in node.align]
                #alignments = ["%d-%d"%(magicCount,int(align.split("-")[1])-1) for align in node.align]
                magicCount += 1
                return (tibFormat("%s"%node.label[1][0]),alignments,"child")
                #return (tibFormat("%s"%node.label[1][1]),alignments,"child")
            else:       
               
                state = "q"
                if node.rule == "DL":
                    #state = ("".join([y.tags[x] for y in node.children for x in sorted(y.tags.keys())])).lower()
                    if state == "": state = "delex"
                if node.label[1][0] == "root" and node.rule != "DL":
                    state = "root"

                return ("%s"%tibFormat(node.label[1][0]),[],state)

        def hedge_combiner(something):
            return something[0]

        tree = self.getDag()
        (ptb,a,state) = tree.dfs(combiner = combiner, extractor = extractor, hedge_combiner = hedge_combiner)[0]
        a = " ".join(i for i in a)

        return (ptb,a)
