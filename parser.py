from pyparsing import *
import logging

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

test_query = "R(x1),X(s1,y1) || S(x2, y2), T(x2)"

varname = Word(alphas, alphanums).setResultsName('vars', listAllMatches=True)
tablename = Word(alphas.upper(), exact=1).setResultsName('table', listAllMatches=True)
table = (tablename + '(' + (varname + ZeroOrMore(',' + varname)) + ')').setResultsName('clause', listAllMatches=True)
conj = (table+ ZeroOrMore(',' + table)).setResultsName('conj', listAllMatches=True)
query = (conj + ZeroOrMore('||' + conj)).setResultsName('query', listAllMatches=True)

parsed_query = query.parseString(test_query, parseAll=True)
print(parsed_query.dump())

print("\n Doing lifted inference... \n")

def lift(Q, P):
    _LOGGER.info("working on query : {}".format(''.join(Q)))

    # recursion base case
    if len(Q.table) == 1:
        grounded = P.lookup(Q.table.pop(), Q.vars)
        if grounded:
            _LOGGER.info("Lookup prob for {} = {}".format(''.join(Q), grounded))
            #P.lookup Q in the future
            return grounded

    if len(Q.conj) > 1:
        # independent if share no tables
        # finds decomposable disjunction
        q1, q2 = None, None
        for conj in Q.conj:
            if q1 is None:
                q1 = query.parseString(''.join(conj))
            if not (set(q1.table) & set(conj.table)):
                q2 = query.parseString(''.join(conj))
                break

        if q1 and q2:
            _LOGGER.info("found decomposable disjunction q1: {} and q2: {}".format(''.join(q1), ''.join(q2)))
            return 1-((1-lift(q1, P)) * (1-lift(q2, P)))
        else:
            _LOGGER.info("Use inclusion-exclusion")

    if len(Q.conj) == 1:
        #try to find a decomposable conjunction (indpendent if doesn't share tables or vars)
        q1, q2 = None, None
        for clause in Q.clause:
            if q1 is None:
                q1 = query.parseString(''.join(clause))
            if not (set(q1.vars) & set(clause.vars) or set(q1.table) & set(clause.table)):
                q2 = query.parseString(''.join(clause))
                break

        # decomposable conjunction
        if q2 and q2:
            _LOGGER.info("found decomposable conjunction q1: {} and q2: {}".format(''.join(q1), ''.join(q2)))
            return lift(q1, P) * lift(q2, P)

        # try to find a seperator variable only 
        seperator_var_set = set.intersection(*[set(clause.vars) for clause in Q.clause])
        if seperator_var_set:
            seperator_var = seperator_var_set.pop()
            _LOGGER.info("found decomposable quantifier with sep var: {}".format(seperator_var))

            print(P.ground(Q.table.pop(), Q.vars))
            return


    # decomposable universal quantifier
    raise ValueError("Query {} is non-heirarchical!".format(Q))


class PDB():

    R = {('1',): 0.4}
    X = {('1','1'): 0.4}
    S = {('1','1'): 0.4}
    T = {('1',): 0.4}

    def lookup(self, table, var):
        try:
            return getattr(self, table)[tuple(var)]
        except Exception:
            return False

    def ground(self, table, var):
        return [key for key in getattr(self, table)]
            

pdb = PDB()
_LOGGER.info(lift(parsed_query, pdb))

