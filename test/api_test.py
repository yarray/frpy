from helper import record
from frpy.api import Stream
from frpy.api import fmap, sequence, repeat, scan, changed, \
    where, merge, trace, flatten, diff, each, timeout, fmap_async, \
    delay


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


def test_changed():
    src = Stream(None)
