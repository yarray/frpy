import time
from typing import TypeVar, List, Tuple
from .core import Stream

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')


def timeout(t: R, responds: Stream[T], s: Stream[S]) -> Stream[R]:
    """ inject a timeout event if t seconds pass after the last
    event of the source stream and no event from the responding stream has
    arrived, the source stream and the responding stream can be the same

    >>> clk = Stream(None)
    >>> clk.clock = clk
    >>> requests = Stream(clk)
    >>> responds = Stream(clk)
    >>> s = timeout(2, responds, requests)
    >>> s.hook = print
    >>> requests(0)
    >>> clk(0)
    >>> responds(0)
    >>> requests(0)
    >>> clk(1)
    >>> clk(2)
    >>> clk(3)
    >>> clk(4)
    4
    >>> clk(5)
    >>> responds(0)

    Parameters
    ----------
    t : float
        limit of elapsed time
    responds : Stream[T]
        responding stream to s
    s : Stream[S]
        source stream (request stream)

    Returns
    -------
    Stream[float]
        timestamps of timeout
    """
    buffer = [time.time()]
    res: Stream[R] = Stream(s.clock)

    # TODO: use combine
    def on_s(src, value):
        buffer[0] = res.clock()

    def on_respond(src, value):
        buffer[0] = None

    def on_clock(clock, value):
        if buffer[0] is not None and res.clock() - buffer[0] > t:
            res(res.clock())
            buffer[0] = None

    responds.listeners.append(on_respond)
    s.clock.listeners.append(on_clock)
    s.listeners.append(on_s)

    return res


def delay(t: R, s: Stream[T]) -> Stream[T]:
    """ delay every events by specific time
    when delayed t is 0, delay every events by a tick

    >>> clk = Stream(None)
    >>> clk.clock = clk
    >>> src = Stream(clk)
    >>> s = delay(2, src)
    >>> s.hook = print
    >>> src(0)
    >>> clk(0)
    >>> src(1)
    >>> clk(1)
    >>> src(2)
    >>> clk(2)
    0
    >>> clk(3)
    1
    >>> clk(4)
    2

    Parameters
    ----------
    t : float
        delayed seconds
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[T]
    """
    buffer: List[Tuple[R, T]] = []
    res: Stream[T] = Stream(s.clock)

    def on_t(src, now):
        for item in list(buffer):
            v_t, v = item
            if now - v_t >= t:
                res(v_t)
                buffer.remove(item)

    def on_s(src, value):
        buffer.append((res.clock(), value))

    s.clock.listeners.append(on_t)
    s.listeners.append(on_s)

    return res
