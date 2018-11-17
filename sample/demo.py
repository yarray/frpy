import time
import sys
import os
import threading
from typing import Any, Tuple
import random
import math
from functools import partial as bind

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from frpy.api import Stream, fmap, repeat, scan, changed, \
    where, merge, trace, flatten, diff, each, timeout, fmap_async, \
    clock, this_tick, next_tick  # noqa: E402
from frpy.fp import const  # noqa: E402


def main():
    counter1 = iter(range(1, 1000))
    counter2 = iter(range(-1, -1000, -1))

    clk, tick = clock()
    sp = fmap(lambda _: next(counter1), repeat(1, clk))
    sn = fmap(lambda _: next(counter2), repeat(2, clk))
    sns = scan(lambda acc, x: acc + x, 0, sn)
    spu = changed(lambda x, y: x == y, sp)
    spuf = where(lambda x: x % 3 != 0, spu)
    sm = merge([spuf, sns])
    ss = trace(lambda x: x % 2, 9999, sm)
    sst = flatten(fmap(lambda s: diff(lambda x, y: y - x, 0, s), ss))
    sst.trace = print
    sp(2)
    sp(1)
    sp(1)

    sstop = fmap(lambda _: 'stop', repeat(5, clk))
    sto = timeout(1.5, sstop, sn)
    events = merge([sn, sstop, sto])
    events.trace = print

    tick()


def amain():
    clk, tick = clock()
    counter1 = iter(range(1, 1000))
    sp = fmap(lambda _: next(counter1), repeat(1, clk))

    async def mult2(s):
        async for e in s:
            if e % 5 != 0:
                yield e * 2

    sp2 = fmap_async(mult2, sp)
    sp2.trace = print
    tick()


def amain2():
    def feed(clk, s):
        time.sleep(1)
        next_tick(clk, lambda: s(5))
        next_tick(clk, lambda: s(4))
        next_tick(clk, lambda: s(3))
        next_tick(clk, lambda: s(2))
        next_tick(clk, lambda: s(1))

    async def print_stream(s):
        async for value in s:
            print(value)
            yield

    clk, tick = clock()

    s: Stream[Any] = Stream(clk)
    fmap_async(print_stream, s)
    threading.Thread(target=feed, args=[clk, s]).start()
    tick()


def print_s(title):
    def f(*args):
        print(title + ': ', *args)

    return f


def timing():
    clk, tick = clock()
    a = fmap(lambda _: 1, repeat(0.3, clk))
    b = fmap(lambda _: 22222222, a)
    each(print, merge([a, b]))
    tick()


value_thres = 3
time_thres = 1.2


def compl():
    # if the sum of a stream is greater than 5, then flush, add from 0,
    # if after 10 seconds the goal is not reached, then flush fail, add from 0
    clk, tick = clock()
    sp = fmap(lambda _: random.random(), repeat(0.2, clk))
    term = Stream(clk)

    def batch(acc, v):
        if v < 0:
            return 0
        else:
            return acc + v

    interrupt = fmap(const(-1), timeout(time_thres, term, term))
    value = merge([sp, fmap(const(-1), term)])
    acc = scan(batch, 0, value)
    met = changed(lambda x, y: x is None or y <= value_thres, acc)
    each(term, merge([met, interrupt]))
    acc.trace = print_s('acc')
    met.trace = bind(print, 'met!')
    interrupt.trace = bind(print, 'fail!')
    tick()


def compl2():
    # compl using async transformation
    clk, tick = clock()
    sp = fmap(lambda _: random.random(), repeat(0.2, clk))

    async def fn(s):
        acc = 0
        last = math.inf
        async for topic, v in s:
            if topic == 'clock':
                if acc > value_thres:
                    met = True
                if v - last > time_thres or acc > value_thres:
                    yield 'met' if met else 'fail'
                    yield 0
                    met = False
                    acc = 0
                    last = v

            elif topic == 'value':
                acc += v
                yield acc

    res = fmap_async(fn, merge([clk, sp], ['clock', 'value']))
    res.trace = print
    tick()


def compl3():
    clk, tick = clock()
    sp = fmap(lambda _: random.random(), repeat(0.2, clk))
    events = merge([clk, sp], ['clock', 'value'])
    out = Stream(clk)
    out.trace = print

    def update(state: Tuple[float, float], event) -> Tuple[float, float]:
        channel, data = event
        start_at, acc = state
        if channel == 'clock':
            if data - start_at > time_thres:
                out('failed')
                return (data, 0)
            return state
        if channel == 'value':
            new_value = acc + data
            out(new_value)
            if new_value >= value_thres:
                out('met')
                return (time.time(), 0)
            return (start_at, new_value)
        else:
            return state

    scan(update, (time.time(), 0), events)
    tick()


def action_q():
    clk, tick = clock()
    events = Stream(clk)

    def update(state: float, event) -> float:
        channel, data = event
        acc = state
        if channel == 'reset':
            return 0
        else:
            acc += data
            if acc >= 3:
                events(('reset', None))
            return acc

    sp = fmap(const(('value', 1)), repeat(0.4, clk))
    each(events, sp)
    states = scan(update, 0, events)
    states.trace = print
    tick()


if __name__ == '__main__':
    # main()
    # amain()
    # amain2()
    # compl()
    # compl2()
    # compl3()
    action_q()
