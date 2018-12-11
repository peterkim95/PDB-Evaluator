import os
import lift
import pytest
import math


@pytest.fixture
def basic_lifter():
    class args(object):
        def __init__(self):
            self.table = ['data/table_files/T1.txt',\
                    'data/table_files/T2.txt',\
                     'data/table_files/T3.txt']
    return lift.Lifter(args()) 


def test_basic(basic_lifter):
    queries = [
        'Q(x1)']
       #'R(x1, y1) || Q(x1)']
       #'R(x1, y1)|| P(x1)|| Q(x2)|| R(x2, y2)',]
    
    expected_ps = [1-.3*.7*.5]
    #        1-(.3*.7*.5 * .2*.6*.5*.4*.1)\
    #]
    for query, expected_p in zip(queries, expected_ps):
        assert(math.isclose(basic_lifter.lift(query),expected_p))


# def test_nell_noindex():
    # pass


