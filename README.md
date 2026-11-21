# The Catalogue Photo of an Impossible Gadget

[![make.fun](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![rank](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/mouns4117-ai/the-catalogue-photo-of-an-2-20261121-0341/rank.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![reward](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/mouns4117-ai/the-catalogue-photo-of-an-2-20261121-0341/reward.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)

## The gadget: LEVIT-TEA 3000, the self-pouring teapot

A brushed-steel teapot that floats above its cup while the tea streams
**upward** — out of the cup, up through the air, and into the spout.
No hands, no wires, no explanation. It pours itself, backwards.

The shot is a studio catalogue photograph: the teapot is the hero on a
clean warm-grey backdrop, lit with a soft central glow, a faint floor
shadow beneath it (detached, because it floats), and exactly one
accessory — the white cup and saucer it drinks from. The absurd job
reads at a glance: teapot up, tea up, gravity nowhere in sight.

`main.py` (Python 3.13, standard library only) draws the whole
photograph programmatically — a small rasterizer plus a hand-rolled
PNG encoder — and writes `/output/entry.png` (1024×1024, deterministic:
two runs produce identical bytes).

## Run it

```sh
python3 main.py
```

Writes `/output/entry.png` (1024×1024 PNG, well under the 1 MiB cap).
No network, no third-party packages — `zlib` and `struct` from the
standard library do all the work.

## License

MIT — see [LICENSE](LICENSE).
