from frpy.api import Stream
from frpy.core import combine
from helper import record


def test_event_order():
    """ event of streams """
    trace = []
    clk = Stream(None)
    s1 = Stream(clk)
    s2 = Stream(clk)
    s3 = Stream(clk, trace.append)
    clk.listeners.append(lambda _, t: s1(t))
    s1.listeners.append(lambda _, x1: s2(x1 + 10))
    s1.listeners.append(lambda _, x1: s3(x1))
    s2.listeners.append(lambda _, x2: s3(x2))
    clk(1)
    assert trace == [1, 11]


def test_combine_deps():
    # Sum two stream values when either changes
    s1 = Stream(None)
    s2 = Stream(None)

    def sum_upstreams(deps, s, src, value):
        return sum(dep() for dep in deps if dep() is not None)

    # existing value will also be pushed
    s1(1)
    s = record(combine(sum_upstreams, [s1, s2]))
    s2(3)
    s1(2)
    s1(5)
    s2(6)
    assert s.footprint == [1, 4, 5, 8, 11]
