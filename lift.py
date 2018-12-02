from pyparsing import *
import logging
from functools import reduce 
import itertools
import operator
import traceback
import math
from pprint import pprint

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# test_query = "P(x1) || Q(x2)"
# test_query = "R(x1, y1), Q(x1)"
test_query = "R(x1, y1), P(x1), Q(x2), R(x2, y2)"
# not (test_quiery

varname = Word(alphas, alphanums).setResultsName('vars', listAllMatches=True)
tablename = Word(alphas.upper(), exact=1).setResultsName('table', listAllMatches=True)
clause = (tablename + '(' + (varname + ZeroOrMore(',' + varname)) + ')').setResultsName('clause', listAllMatches=True)
conj = (clause + ZeroOrMore(',' + clause)).setResultsName('conj', listAllMatches=True)
query = (conj + ZeroOrMore('||' + conj)).setResultsName('query', listAllMatches=True)


print("\n Doing lifted inference... \n")


def invert(f):
    return 1 - f()
def lift(query_string, pdb, subsitutions, invert=False):

    def pretty(Q):
        formatted = ''.join(Q)
        for var in subsitutions:
            formatted = formatted.replace(var, subsitutions[var])
        return formatted

    def set_vars(x):
        return set(x.vars)

    # for finding independence (connected components)
    def union_find(lis):
        lis = map(set, lis)
        unions = []
        for item in lis:
            temp = []
            for s in unions:
                if not s.isdisjoint(item):
                    item = s.union(item)
                else:
                    temp.append(s)
            temp.append(item)
            unions = temp
        return unions

    if (invert):
        return  1-lift(query_string, pdb, subsitutions, invert=False)

    indent = '.....' * (len(traceback.extract_stack()) - 2)
    if len(traceback.extract_stack()) > 50:
        raise ValueError("Recursion")

    Q = query.parseString(query_string)
    _LOGGER.info("{} LIFT: working on query: {} with subsitutions: {}".format(indent, pretty(Q), subsitutions))
   
    # base case of recursion, 1 table and vars all instantiated 
    if len(Q.table) == 1 and subsitutions.keys() == set(Q.vars):
        table = Q.table.pop()
        prob = pdb.lookup(table, (subsitutions[v] for v in Q.vars))
        _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
        return prob

    if len(Q.conj) > 1:
        def dependent(combination):
            q1, q2 = combination
            return set(q1.table) & set(q2.table) or set(q1.vars) & set(q2.vars) - subsitutions.keys()

        def make_clause(x):
            return map(''.join, x)

        test = map(make_clause, filter(dependent, itertools.combinations(Q.clause, 2)))
        dependent_components = union_find(test)
        if not dependent_components:
            dependent_components = [{''.join(clause)} for clause in Q.clause]

        print(dependent_components)

        # all independent
        if len(dependent_components) > 1 :
            _LOGGER.info("{} DECOMPOSABLE DISJUNCTION:  {} ".format(indent, dependent_components))
            prob = 1-reduce(operator.mul, map(lambda x: 1-lift(''.join(x), pdb, subsitutions), dependent_components))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

        else:
            # at this point we know its one big disjunction
            _LOGGER.info("{} INCLUSION EXCLUSION: query {}".format(indent, pretty(Q)))
            test = [''.join(c) for c in Q.clause]
            print(test)
            a = [math.pow(-1, i) * sum(map(lambda x: lift(','.join(x), pdb, subsitutions), itertools.combinations(test, i+1))) for i in range(len(Q.conj))]
            raise ValueError()
            prob = sum(a)
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

    # now we are only dealing with conjunctions 
    if len(Q.conj) == 1:

        #indepndent if q1 and q2 have different tables and vars not in subsitutions
        def dependent(combination):
            q1, q2 = combination
            return set(q1.table) & set(q2.table) or set(q1.vars) & set(q2.vars) - subsitutions.keys()

        def make_clause(x):
            return map(''.join, x)

        #shitty way of doing this but whatever
        test = map(make_clause, filter(dependent, itertools.combinations(Q.clause, 2)))
        dependent_components = union_find(test)
        if not dependent_components:
            dependent_components = [{''.join(clause)} for clause in Q.clause]

        print(dependent_components)

        # all independent
        if len(dependent_components) > 1 :
            _LOGGER.info("{} DECOMPOSABLE CONJUNCTION: {} ".format(indent, dependent_components))
            prob = reduce(operator.mul, map(lambda x: lift(','.join(x), pdb, subsitutions), dependent_components))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

        # try to find a seperator variable only 
        seperator_var_set = set.intersection(*[set(clause.vars) for clause in Q.clause]) - subsitutions.keys()
        if seperator_var_set:
            seperator_var = seperator_var_set.pop()
            _LOGGER.info("{} DECOMPOSABLE QUANTIFIER: query {} has separator var: {}".format(indent, pretty(Q), seperator_var))

            def generate_grounding(seperator_var, grounding):
                new = subsitutions.copy()
                new[seperator_var] = grounding
                return new

            def get_possible_vals(clause):
                return pdb.ground(clause.table.pop(), list(clause.vars).index(seperator_var))

            # note that a grounding is only non-zero if it's present in all of the tables, so we can use intersection here
            new_subsitutions = [generate_grounding(seperator_var, grounding) for grounding in set.intersection(*map(get_possible_vals, Q.clause))]
            _LOGGER.info("{} creating {} new subsitutions: {}".format(indent, len(new_subsitutions), new_subsitutions))
            prob = 1 - reduce(operator.mul, map(lambda x: 1-lift(query_string, pdb, x), new_subsitutions))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

    # decomposable universal quantifier
    raise ValueError("Query {} is non-heirarchical!".format(pretty(Q)))

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
            key = tuple(var)
            # print("Doing lookup for {}".format(key))
            a = getattr(self, table)[key]
            # print("found {}".format(a))
            return a
        except Exception as e:
            # _LOGGER.exception(e)
            return 0

    def ground(self, table, varindex):
        return set([key[varindex] for key in getattr(self, table)])
            

pdb = PDB()
parsed_query = query.parseString(test_query)
# print(parsed_query.dump())
_LOGGER.info(lift(test_query, pdb, dict()))


