from pyparsing import *
import logging
from functools import reduce
import operator
import traceback

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# test_query = "R(x1),X(x1,y1) || S(x2, y2), T(x2)"
test_query_2 = "R(x1, y1), Q(x1)"
test_query_1 = "R(x1, y1), P(x1), Q(x2), R(x2, y2)"

varname = Word(alphas, alphanums).setResultsName('vars', listAllMatches=True)
tablename = Word(alphas.upper(), exact=1).setResultsName('table', listAllMatches=True)
clause = (tablename + '(' + (varname + ZeroOrMore(',' + varname)) + ')').setResultsName('clause', listAllMatches=True)
conj = (clause + ZeroOrMore(',' + clause)).setResultsName('conj', listAllMatches=True)
query = (conj + ZeroOrMore('||' + conj)).setResultsName('query', listAllMatches=True)

print("\n Doing lifted inference... \n")

def lift(Q, pdb, subsitutions):
    
    def pretty(Q):
        formatted = ''.join(Q)
        for var in subsitutions:
            formatted = formatted.replace(var, subsitutions[var])
        return formatted

    indent = '...' * (len(traceback.extract_stack()) - 2)

    _LOGGER.info("{} LIFT: working on query: {} with subsitutions: {}".format(indent, pretty(Q), subsitutions))

    # base case of recursion, 1 table and vars all instantiated 
    if len(Q.table) == 1 and subsitutions.keys() == set(Q.vars):
        table = Q.table.pop()
        prob = pdb.lookup(table, (subsitutions[v] for v in Q.vars))
        _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
        return prob

    if len(Q.conj) > 1:
        # finds decomposable disjunction
        q1, q2 = None, None
        for conj in Q.conj:
            if q1 is None:
                q1 = query.parseString(''.join(conj))
            # independent if share no tables (all vars distinct as given, so this is okay)
            if not (set(q1.table) & set(conj.table)):
                q2 = query.parseString(''.join(conj))
                break

        if q1 and q2:
            _LOGGER.info("{} DECOMPOSABLE DISJUNCTION: q1: {} and q2: {}".format(indent, pretty(q1), pretty(q2)))
            prob = 1-((1-lift(q1, pdb, subsitutions))\
                     *(1-lift(q2, pdb, subsitutions)))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

        else:
            #TODO figure out inclusion exclusion
            _LOGGER.info("Use inclusion-exclusion")

    # now we are only dealing with conjunctions 
    if len(Q.conj) == 1:
        #indepndent if q1 and q1 have different tables and vars not in subsitutions


        def find_independent(Q):
            q1, q2 = '', ''
            for clause in Q.clause:
                print(clause)
                #set as first
                if q1 is None:
                    q1 += ''.join(clause)
         
                if not (set(q1.vars) & set(clause.vars) - subsitutions.keys() or set(q1.table) & set(clause.table)):
                    q2 += ''.join(clause)
                    break
            return query.parseString(q1), query.parseString(q2)

        q1, q2 = find_independent(Q)

        # decomposable conjunction
        if q2 and q2:
            _LOGGER.info("{} DECOMPOSABLE CONJUNCTION: q1: {} and q2: {}".format(indent, pretty(q1), pretty(q2)))
            prob = lift(q1, pdb, subsitutions) * lift(q2, pdb, subsitutions)
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

        # try to find a seperator variable only 
        seperator_var_set = set.intersection(*[set(clause.vars) for clause in Q.clause]) - subsitutions.keys()
        if seperator_var_set:
            seperator_var = seperator_var_set.pop()
            _LOGGER.info("{} DECOMPOSABLE QUANTIFILER: query {} has separator var: {}".format(indent, ''.join(Q), seperator_var))

            def generate_grounding(seperator_var, grounding):
                new = subsitutions.copy()
                new[seperator_var] = grounding
                return new

            # note that a grounding is only non-zero if it's present in all of the tables, so we can use intersection here
            possible_values = set.intersection(*[pdb.ground(clause.table.pop(), list(clause.vars).index(seperator_var)) for clause in Q.clause])
            new_subsitutions = [generate_grounding(seperator_var, grounding) for grounding in possible_values]
            _LOGGER.info("{} creating {} new subsitutions: {}".format(indent, len(new_subsitutions), new_subsitutions))
            prob = 1 - reduce(operator.mul, map(lambda x: 1-lift(Q, pdb, x), new_subsitutions))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

    # decomposable universal quantifier
    raise ValueError("Query {} is non-heirarchical!".format(''.join(Q)))

class PDB():

    P = {
            ('0',): 0.7, 
            ('1',): 0.8, 
            ('2',): 0.6, 
        }

    Q = {
            ('0',): 0.7, 
            ('1',): 0.3, 
            ('2',): 0.5, 
        }

    R = {
            ('0','0'): 0.8,
            ('0','1'): 0.4,
            ('0','2'): 0.5,
            ('1','2'): 0.6,
            ('2','2'): 0.9,
        }


    def lookup(self, table, var):
        try:
            return getattr(self, table)[tuple(var)]
        except Exception as e:
            return 0

    def ground(self, table, varindex):
        return set([key[varindex] for key in getattr(self, table)])
            

pdb = PDB()
parsed_query  = query.parseString(test_query_1, parseAll=True)
_LOGGER.info(lift(parsed_query, pdb, dict()))

