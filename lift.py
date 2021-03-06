from pyparsing import *
import logging
from functools import reduce
import itertools
import operator
import traceback
import math
from timeit import default_timer as timer

from pprint import pprint
from db import SQLDatabase

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)

class Lifter:

    # test_query = "Q(x1)"
    # test_query = "R(x1, y1) || Q(x1)"
    # test_query = "R(x1, y1)|| P(x1)|| Q(x2)|| R(x2, y2)"

    # E abcd (a and b and c and d)
    # !A abcd !(a and b and c and d)
    #         !a or !b or !c or !d

    # E abcd (a and  b)  or (c and d)


    # !A abcd !((a and b) or (c and d))
    #         !((a and b) or (c and d))
    #         !(a and  b) and !(c and d)
    #
    # !A abcd (!a or !b) and  (!c or !d)

    def __init__(self, args):
        self.pdb = SQLDatabase(db_name=getattr(args,'db_name', ':memory:'),
                table_files=getattr(args,'table', []),
                create_index=getattr(args, 'index', False),
        )    
        
        varname = Word(alphas, alphanums).setResultsName('vars', listAllMatches=True)
        tablename = Word(alphas).setResultsName('table', listAllMatches=True)
        clause = (tablename + '(' + (varname + ZeroOrMore(',' + varname)) + ')').setResultsName('clause', listAllMatches=True)
        conj = (clause + ZeroOrMore(',' + clause)).setResultsName('conj', listAllMatches=True)
        self.query = (conj + ZeroOrMore('||' + conj)).setResultsName('query', listAllMatches=True)
        self.use_speedup = getattr(args, 'speedup', False)

    def _lift_helper(self, query_string, subsitutions, invertProbs=False, invertLiterals=True):
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
        Q = self.query.parseString(query_string)
        _LOGGER.info("{} LIFT: working on query: {} with subsitutions: {}".format(indent, pretty(Q), subsitutions))

        if self.use_speedup:
            # Speedup of a base case when there's only 1 var left to ground
            if len(Q.table) == 1 and len(subsitutions.keys()) == len(set(Q.vars)) - 1:
                table = Q.table.pop()
                missing_var = set(Q.vars).difference(subsitutions.keys()).pop()
                almost_Q = [x for x in Q.vars if x != missing_var]
                tuple_probs = [row[0] for row in self.pdb.getcol(table, 
                    (subsitutions[v] for v in almost_Q), missing_var)]
                if invertProbs:
                    tuple_probs = [1 - x for x in tuple_probs]
                prob = reduce(lambda x,y: x * y, tuple_probs)
                _LOGGER.info("{} RESULT: Prob of query: {} with returned probabilities {} = {}"
                    .format(indent, pretty(Q), tuple_probs, prob))
                return prob
        # base case of recursion, 1 table and vars all instantiated
        if len(Q.table) == 1 and subsitutions.keys() == set(Q.vars):
            table = Q.table.pop()
            prob = self.pdb.lookup(table, (subsitutions[v] for v in Q.vars))
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
                prob = 1-reduce(operator.mul, map(lambda x: 1-self._lift_helper(','.join(x), subsitutions, invertProbs=True), dependent_components))
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
                _LOGGER.info(varstest)

                #break on varset (possible to run inclusion exclusion)
                if len(varstest) > 1:

                    def merge(combination):
                        #base case
                        if len(combination) == 1:
                            return ''.join(combination[0])

                        #see if there is clause to be factored out
                        subqueries = list(map(self.query.parseString, combination))
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


                    prob = sum([math.pow(-1, i) * sum(map(lambda x: self._lift_helper(merge(x), subsitutions), itertools.combinations(varstest, i+1))) for i in range(len(varstest))])
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
            prob = reduce(operator.mul, map(lambda x: self._lift_helper(''.join(x), subsitutions), dependent_components))
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
                return self.pdb.ground(clause.table.pop(), list(clause.vars).index(seperator_var))

            # note that a grounding is only non-zero if it's present in all of the tables, so we can use intersection here
            new_subsitutions = [generate_grounding(seperator_var, grounding) for grounding in set.intersection(*map(get_possible_vals, Q.clause))]
            _LOGGER.info("{} creating {} new subsitutions: {}".format(indent, len(new_subsitutions), new_subsitutions))
            prob =  reduce(operator.mul, map(lambda x: self._lift_helper(query_string, x), new_subsitutions))
            _LOGGER.info("{} RESULT: Prob of query: {} = {}".format(indent, pretty(Q), prob))
            return prob

        raise ValueError("Query: {} is non-heirarchical!".format(pretty(Q)))


    def lift(self, query):
        start_time = timer()
        answer = 1 - self._lift_helper(query, dict(), invertLiterals=True)
        end_time = timer()
        _LOGGER.info(' FINAL RESULT: P({}) = {} ({}ms)'.format(query, answer, (end_time - start_time) * 1000))
        return answer


def main():
    class args(object):
        def __init__(self):
            self.table = ['data/table_files/T1.txt', 'data/table_files/T2.txt', 'data/table_files/T3.txt']
            # self.table = []
            # self.db_name = 'nell_noindex.db'
            self.speedup = False
            # self.index = True
            # self.is_nell = True
    print(Lifter(args()).lift('R(x1, y1) || P(x1) || Q(x2) || R(x2,y2)'))
    # print(Lifter(args()).lift('generalizations(x1, y1)'))

if __name__ == '__main__':
    main()
