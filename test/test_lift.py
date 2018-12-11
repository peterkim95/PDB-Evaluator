import os
import lift
import pytest

def isclose(n1,n2, ndigits=2):
    return round(n1, ndigits) == round(n2, ndigits)


@pytest.fixture
def basic_lifter():
    class args(object):
        def __init__(self):
            self.table = ['data/table_files/T1.txt',\
                    'data/table_files/T2.txt',\
                     'data/table_files/T3.txt']
    return lift.Lifter(args()) 


def test_basic_pass(basic_lifter):
    queries = [
        'Q(x1)',\
       'R(x1, y1) || Q(x1)'\
       ]
    
    expected_ps = [1-.3*.7*.5,\
            0.8458
    ]
    for query, expected_p in zip(queries, expected_ps):
        assert(isclose(basic_lifter.lift(query),expected_p))

def test_basic_fail(basic_lifter):
    queries= ['R(x1, y1)|| P(x1)|| Q(x2)|| R(x1, x2)']

    for query in queries:
        with pytest.raises(ValueError):
            basic_lifter.lift(query)
            pass
# def test_nell_noindex():
    # pass


