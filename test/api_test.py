from helper import record
from frpy.api import Stream
from frpy.api import fmap, sequence, repeat, scan, changed, \
    where, merge, trace, flatten, diff, each, timeout, fmap_async, \
    delay


def test_repeat_fraction():
    clk = Stream(None)
    clk.clock = clk
    s = record(repeat(2.5, clk))
    clk(0)
    clk(1)
    clk(2)
    clk(3)
    clk(4)
    clk(5)
    clk(6)
    assert s.footprint == [0, 3, 6]


def test_sequence_ended():
    clk = Stream(None)
    clk.clock = clk
    s = record(sequence(2, iter(range(42, 46, 2)), clk))
    clk(0)
    clk(1)
    clk(2)
    clk(3)
    clk(4)
    clk(5)
    clk(6)
    clk(7)
    clk(8)
    assert s.footprint == [42, 44]


def test_fmap():
    src = Stream(None)
    s = record(fmap(lambda x: x + 3, src))
    src(5)
    src(208)
    src(176)
    src(1021)
    assert s.footprint == [8, 211, 179, 1024]


def test_scan():
    src = Stream(None)
    s = record(scan(lambda acc, x: acc + x, -1, src))
    src(2)
    src(6)
    src(10)
    assert s.footprint == [1, 7, 17]


def test_scan_no_init():
    src = Stream(None)
    s = record(scan(lambda acc, x: acc + ' ' + x, None, src))
    src('hello')
    src('world,')
    src('frpy!')
    assert s.footprint == ['hello', 'hello world,', 'hello world, frpy!']


def test_diff():
    src = Stream(None)
    s = record(diff(lambda x, y: y != x, '', src))
    src('aaa')
    src('aaa')
    src('bbb')
    src('aaa')
    src('bbb')
    assert s.footprint == [True, False, True, True, True]


def test_diff_no_init():
    src = Stream(None)
    s = record(diff(lambda x, y: y - x, None, src))
    src(5)
    src(11)
    src(19)
    assert s.footprint == [5, 6, 8]


def test_trace_stale():
    src = Stream(None)
    s = trace(lambda x: x // 10, 0, src)
    footprints = []

    def update_footprints(sub):
        i = len(footprints)
        footprints.append([sub()])
        sub.hook = footprints[i].append

    s.hook = update_footprints
    src(1)
    src(21)
    src(2)
    src(15)
    src(11)
    src(7)
    assert footprints == [[1], [21], [2], [15], [11], [7]]


def test_merge_topic():
    s1 = Stream(None)
    s2 = Stream(None)
    s3 = Stream(None)
    s = record(merge([s1, s2, s3], ['s1', 's2', 's3']))
    s1(123)
    s2(456)
    s1(12)
    s1(42)
    s3(500)
    s2(789)
    assert s.footprint == [('s1', 123), ('s2', 456), ('s1', 12), ('s1', 42),
                           ('s3', 500), ('s2', 789)]
