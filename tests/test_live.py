"""The live loop must survive a feed that goes quiet for longer than the status interval."""
import asyncio
import types

from mmsim import live
from mmsim.events import Quote


def test_quiet_feed_does_not_end_the_session(monkeypatch):
    async def stream(symbol):
        for i in range(3):
            yield Quote(i, "x", 1.0, 1.0, 1.1, 1.0)
            await asyncio.sleep(0.3)  # longer than tick_s below

    monkeypatch.setattr(live, "get_feed", lambda venue: types.SimpleNamespace(stream=stream))
    got, ticks = [], []
    asyncio.run(live._run("fake", "X", minutes=1.0 / 60, on_event=got.append, on_tick=lambda: ticks.append(1),
                          tick_s=0.1))
    assert [e.ts for e in got] == [0, 1, 2]  # all events, despite 0.3 s gaps > 0.1 s tick
    assert len(ticks) >= 3
