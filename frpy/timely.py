import time
import math
from typing import TypeVar
from .core import Stream

T = TypeVar('T')
S = TypeVar('S')


def timeout(t: float, responds: Stream[T], s: Stream[S]) -> Stream[float]:
    """ inject a timeout event if t seconds pass after the last
    event of the source stream and no event from the responding stream has
    arrived, the source stream and the responding stream can be the same

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
    res: Stream[float] = Stream(s.clock)

    def on_s(src, value):
        buffer[0] = time.time()

    def on_respond(src, value):
        buffer[0] = None

    def on_clock(clock, value):
        if buffer[0] is not None and s.clock() - buffer[0] > t:
            res(s.clock())
            buffer[0] = None

    responds.listen(on_respond)
    s.clock.listen(on_clock)
    s.listen(on_s)

    return res


def delay(t: float, s: Stream[T]) -> Stream[T]:
    """ delay every events by specific time
    when delayed t is 0, delay every events by a tick

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
    clock_buffer = [math.inf]
    value_buffer = [None]
    res: Stream[T] = Stream(s.clock)

    def on_t(src, value):
        if value - clock_buffer[0] >= t:
            clock_buffer[0] = math.inf
            res(value_buffer[0])

    def on_s(src, value):
        clock_buffer[0] = s.clock()
        value_buffer[0] = value

    s.clock.listen(on_t)
    s.listen(on_s)

    return res
