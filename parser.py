from pyparsing import *

test_query = "R(x1),X(s1,y1) || S(x2, y2), T(x2)"

varname = Word(alphas, alphanums)
tablename = Word(alphas.upper(), exact=1)
table = tablename.setResultsName('table', listAllMatches=True) + Suppress('(') + \
        delimitedList(varname, delim=',').setResultsName('vars', listAllMatches=True) + Suppress(')')
conj = delimitedList(table, delim=',').setResultsName('conj', listAllMatches=True)
query = delimitedList(conj, delim='||').setResultsName('query', listAllMatches=True)

parsed_query = query.parseString(test_query, parseAll=True)
print(parsed_query.dump())
print("Doing lifted inference")

def lift(Q, P):
    print("working on query : {}".format(Q))
    if len(Q.table) == 1:
        print("Lookup prob for {}".format(''.join(Q)))
        #P.lookup Q in the future
        return 0.5

    if len(Q.conj) > 1:
        # independent if share no tables
        q1, q2 = None, None
        for conj in Q.conj:
            if q1 is None:
                q1 = conj
            if not set(q1.table) & set(conj.table):
                q2 = conj
        
        print("q1: {}".format(q1))
        print("q2: {}".format(q2))
        # existst decomposable disjunction
        if q1 and q2:
            return 1-((1-lift(q1, P)) * (1-lift(q2, P)))

        else:
            print("Use inclusion-exclusion")

    #decomposable conjunction
    if (Q.getName() == 'conj'):
        q1, q2 = None, None
        for t, v in zip(Q.table, Q.vars):
            if q1 is None:
                q1 = (t, v)
            if not ()

    # decomposable universal quantifier
    

    return 0




print(lift(parsed_query, 1))

