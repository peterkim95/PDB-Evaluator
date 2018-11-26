from pyparsing import *
import logging
from functools import reduce
import operator

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

def lift(Q, P, subsitutions):
    _LOGGER.info("working on query : {} with subsitutions: {}".format(''.join(Q), subsitutions))
    
    #all instantiated -> 
    if len(Q.table) == 1:
        table = Q.table.pop()

        if subsitutions.keys() == set(Q.vars):
            _LOGGER.info("all vars instantiated, doing lookup for {} with {} ".format(''.join(Q), subsitutions))
            return P.lookup(table, (subsitutions[v] for v in Q.vars))

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
            return 1-((1-lift(q1, P, subsitutions)) * (1-lift(q2, P, subsitutions)))
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
            return lift(q1, P, subsitutions) * lift(q2, P, subsitutions)

        # try to find a seperator variable only 
        seperator_var_set = set.intersection(*[set(clause.vars) for clause in Q.clause]) - subsitutions.keys()
        if seperator_var_set:
            seperator_var = seperator_var_set.pop()
            _LOGGER.info("found decomposable quantifier with sep var: {}".format(seperator_var))

            def generate_grounding(seperator_var, grounding):
                new = subsitutions.copy()
                new[seperator_var] = grounding
                return new

            new_subsitutions = [generate_grounding(seperator_var, grounding) for grounding in P.ground(Q.table.pop(), list(Q.vars).index(seperator_var))]
            print(new_subsitutions)
            prob = 1 - reduce(operator.mul, map(lambda x: 1-lift(Q, P, x), new_subsitutions), 1)
            _LOGGER.info("prob: {}".format(prob))
            return prob



    # decomposable universal quantifier
    raise ValueError("Query {} is non-heirarchical!".format(''.join(Q)))


class PDB():

    R = {('a',): 0.6}
    X = {('a','a'): 0.7}
    S = {('a','a'): 0.3}
    T = {('a',): 0.2}

    def lookup(self, table, var):
        try:
            return getattr(self, table)[tuple(var)]
        except Exception as e:
            _LOGGER.exception(e)
            return False

    def ground(self, table, varindex):
        return [key[varindex] for key in getattr(self, table)]
            

pdb = PDB()
_LOGGER.info(lift(parsed_query, pdb, dict()))

