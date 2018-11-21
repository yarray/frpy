from typing import TypeVar, Iterator
from .core import Stream, combine

T = TypeVar('T')
S = TypeVar('S')


def repeat(interval: float, clock: Stream[T]) -> Stream[T]:
    """ repeatedly inject unix timestamp

    >>> clk = Stream(None)
    >>> clk.clock = clk
    >>> s = repeat(3, clk)
    >>> s.hook = print
    >>> clk(0)
    0
    >>> clk(1)
    >>> clk(2)
    >>> clk(3)
    3
    >>> clk(4)
    >>> clk(5)
    >>> clk(6)
    6

    Parameters
    ----------
    interval : float
        interval between events
    clock : Stream[T]
        clock stream of world

    Returns
    -------
    Stream[T]
        every interval time units, inject clock event
    """

    def g(deps, this, src, value):
        if this() is None or value - this() >= interval:
            return value

    return combine(g, [clock])


def sequence(interval: float, it: Iterator[S], clock: Stream[T]) -> Stream[S]:
    """ inject next item in iterator

    >>> clk = Stream(None)
    >>> clk.clock = clk
    >>> s = sequence(3, iter(range(5, 10, 2)), clk)
    >>> s.hook = print
    >>> clk(0)
    5
    >>> clk(1)
    >>> clk(2)
    >>> clk(3)
    7
    >>> clk(4)
    >>> clk(5)
    >>> clk(6)
    9

    Parameters
    ----------
    interval : float
        interval between events
    it : Iterator[S]
        the iterator to generate values
    clock : Stream[T]
        clock stream of world

    Returns
    -------
    Stream[S]
        every interval time units, bumps an event
    """
    buffer = [clock()]

    def g(deps, this, src, value):
        if buffer[0] is None or value - buffer[0] >= interval:
            try:
                buffer[0] = value
                return next(it)
            except StopIteration:
                pass

    return combine(g, [clock])
