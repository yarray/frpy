from typing import TypeVar, Iterator
from .core import Stream, combine

T = TypeVar('T')
S = TypeVar('S')


def repeat(interval: float, clock: Stream[T]) -> Stream[T]:
    """ repeatedly inject unix timestamp

    .. code-block:: python

        # every 5 time units, inject current timestamp to s
        clk, tick = clock()
        s = repeat(5, clk)
        tick()

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
    """ inject incremental numbers from 0

    .. code-block:: python

        # every 5 time units, inject 0, 1, 2, 3, ...
        clk, tick = clock()
        s = sequence(5, itertools.count(), clk)
        tick()

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
