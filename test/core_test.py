from frpy.api import Stream


def test_event_order():
    """ event of streams """
    trace = []
    clk = Stream(None)
    s1 = Stream(clk)
    s2 = Stream(clk)
    s3 = Stream(clk, trace.append)
    clk.listen(lambda _, t: s1(t))
    s1.listen(lambda _, x1: s2(x1 + 10))
    s1.listen(lambda _, x1: s3(x1))
    s2.listen(lambda _, x2: s3(x2))
    clk(1)
    assert trace == [1, 11]
