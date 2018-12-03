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

# test_query = "Q(x1)"
# test_query = "R(x1, y1) || Q(x1)"
test_query = "R(x1, y1)|| P(x1)|| Q(x2)|| R(x2, y2)"

# E abcd (a and b and c and d)
# !A abcd !(a and b and c and d)
#         !a or !b or !c or !d

# E abcd (a and  b)  or (c and d)


# !A abcd !((a and b) or (c and d))
#         !((a and b) or (c and d))
#         !(a and  b) and !(c and d)
#
# !A abcd (!a or !b) and  (!c or !d)

varname = Word(alphas, alphanums).setResultsName('vars', listAllMatches=True)
tablename = Word(alphas.upper(), exact=1).setResultsName('table', listAllMatches=True)
clause = (tablename + '(' + (varname + ZeroOrMore(',' + varname)) + ')').setResultsName('clause', listAllMatches=True)
conj = (clause + ZeroOrMore(',' + clause)).setResultsName('conj', listAllMatches=True)
query = (conj + ZeroOrMore('||' + conj)).setResultsName('query', listAllMatches=True)

#number of ands is #of clauses - # of conj

print("\n Doing lifted inference... \n")


def invert_f(f):
    def helper(x):
        return 1-f(x)
    return helper

#first convert the query  to universal and then run the universal alg


def lift(query_string, pdb, subsitutions, invertLiterals=True):
    #helper
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

    def dependent(q1, q2):
        return share_vars(q1, q2) or share_tables(q1, q2)

    def share_vars(q1, q2):
        return set(q1.vars) & set(q2.vars) - subsitutions.keys()

    def share_tables(q1, q2):
        return set(q1.table) & set(q2.table)

    def make_clause(x):
        return map(''.join, x)

    def pretty(Q):
        formatted = ''.join(Q)
        for var in subsitutions:
            formatted = formatted.replace(var, subsitutions[var])
        return formatted

    indent = '  .' * (len(traceback.extract_stack()) - 2)
    Q = query.parseString(query_string)
    _LOGGER.info("{} LIFT: working on query: {} with subsitutions: {}".format(indent, pretty(Q), subsitutions))

    # base case of recursion, 1 table and vars all instantiated
    if len(Q.table) == 1 and subsitutions.keys() == set(Q.vars):
        table = Q.table.pop()
        prob = pdb.lookup(table, (subsitutions[v] for v in Q.vars))
        _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
        if invertLiterals:
            return 1 - prob
        return prob

    if len(Q.conj) > 1:

        test = list(map(make_clause, filter(lambda x: dependent(*x), itertools.combinations(Q.conj, 2))))
        dependent_components = union_find(test)
        if not dependent_components:
            dependent_components = [{''.join(conj)} for conj in Q.conj]

        # all independent
        if len(dependent_components) > 1 :
            _LOGGER.info("{} DECOMPOSABLE DISJUNCTION: {} ".format(indent, dependent_components))
            prob = 1-reduce(operator.mul, map(lambda x: 1-lift(','.join(x), pdb, subsitutions), dependent_components))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

        else:
            _LOGGER.info("{} INCLUSION EXCLUSION: query {}".format(indent, pretty(Q)))

            test = [''.join(c) for c in Q.clause]
            #partition test into (varsets)
            varstest = map(make_clause, list(filter(lambda x: share_vars(*x), itertools.combinations(Q.conj, 2))))
            varstest = union_find(varstest)
            if not varstest:
                varstest = [{''.join(conj)} for conj in Q.conj]

            varstest = list(map('||'.join, varstest))
            print(varstest)

            #break on varset (possible to run inclusion exclusion)
            if len(varstest) > 1:

                def merge(combination):
                    #base case
                    if len(combination) == 1:
                        return ''.join(combination[0])

                    #see if there is clause to be factored out
                    subqueries = list(map(query.parseString, combination))
                    test = set.intersection(*[set(a.table) for a in subqueries])
                    print(test)

                    unifier = None
                    vars_to_convert = []

                    for q in subqueries:
                        for clause in q.clause:
                            if clause.table.pop() in test:
                                if not unifier:
                                    unifier = clause
                                else:
                                    vars_to_convert.append(clause.vars)

                    # print("unifier:", unifier)
                    # print("vars:", vars_to_convert)

                    factored = [','.join(map(''.join, filter(lambda x: x.table.pop() not in test, subq.clause))) for subq in subqueries]
                    print(factored)

                    prev = ','.join(factored)
                    for varthing in vars_to_convert:
                        for var, unify in zip(varthing, unifier.vars):
                            prev = prev.replace(var, unify)

                    return '||'.join([''.join(unifier), prev])


                prob = sum([math.pow(-1, i) * sum(map(lambda x: lift(merge(x), pdb, subsitutions), itertools.combinations(varstest, i+1))) for i in range(len(varstest))])
                _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
                return prob

            _LOGGER.info("INCLUSION-EXCLUSION failed")


    #check for decomposabvle disjunction (just one conj)
    test = map(make_clause, filter(lambda x : dependent(*x), itertools.combinations(Q.clause, 2)))
    dependent_components = union_find(test)
    if not dependent_components:
        dependent_components = [{''.join(clause)} for clause in Q.clause]

    # all independent
    if len(dependent_components) > 1 :
        _LOGGER.info("{} DECOMPOSABLE DISJUNCTION:  {} ".format(indent, dependent_components))
        prob = reduce(operator.mul, map(lambda x: lift(''.join(x), pdb, subsitutions), dependent_components))
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
        prob =  reduce(operator.mul, map(lambda x: lift(query_string, pdb, x), new_subsitutions))
        _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
        return prob

    raise ValueError("Query: {} is non-heirarchical!".format(pretty(Q)))

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
# print(parsed_query.ump())
_LOGGER.info(1 - lift(test_query, pdb, dict(), invertLiterals=True))
