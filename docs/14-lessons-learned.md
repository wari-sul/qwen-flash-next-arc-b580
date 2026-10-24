# 14. Lessons learned

## Hardware and virtualization

1. **"It booted once" is not proof GPU passthrough is safe.** VFIO resets of the Arc B580 stalled the IOMMU on this AMD platform. The warnings were mild until the start that froze the whole host. If a reset can take down the hypervisor, every VM start is a gamble.
2. **LXC + `/dev/dri` is the boring, stable option.** The host keeps the driver, nothing is ever reset, and the container gets full compute access. Unprivileged works fine.
3. **Pinned GPU memory is invisible to container limits.** The model container showed 2 GB used while the host had 47 GB locked. Watch the host's `MemAvailable`, and plan for the pressure to land on whichever *other* container has the tightest limit.
4. **Check every guest after a memory-heavy test,** not only the host total. My watchdog was watching the wrong number when another container got OOM-killed.

## Strata on Arc

5. **The installer is not the only path.** On Arc, `strata launch` will not download or prepare models, but the tools it would run (`iq_pack.py`, `strata_tokenizer.py`, `mtp_fetch.py`, `mtp_pack.py`, `mtp_rt.py`) are in the install and work with the bundled Python. Read `setup.py` to see what it would have done.
6. **A pack mismatch error means "rebuild the pack",** not "this model is unsupported". It takes seconds.
7. **`--kv-resident` is free performance at long context.** Moving the KV cache to pinned RAM gave more VRAM to experts, so 128K and 256K were as fast as 32K.
8. **MTP is a 1.3 to 1.4x speedup with no quality loss** for 839 MiB of VRAM. Turn it on.
9. **Lazy load + idle unload makes a 47 GB model a good neighbour.** The host gets its RAM back 20 minutes after the last request.
10. **One model per server; use a hook to enforce one model per GPU.** `before_load` with a strict unload of the peer is enough.

## Context

11. **Use the native context.** 256K needed no rope scaling, found every needle, and did not slow generation noticeably. 512K with YaRN cost 3 GB more pinned RAM and broke a neighbour. More context is only worth it if you have documents that need it.

## Benchmarking

12. **Validate graders before spending GPU time.** Run the reference solution through every test (it must pass) and the buggy starting code (it must fail). That caught a too-slow reference of mine before it could fail every model.
13. **Read every failure.** Four of my first ten "failures" were my grader picking a usage-example code block. Without reading them I would have reported a 4-point quality gap that did not exist.
14. **Fix the grader, then re-grade everything,** and say so. Re-grading stored answers keeps both models on the same footing; keeping the original logs keeps it honest.
15. **Test the casual prompt, not just the perfect one.** The same task written as a one-paragraph chat message produced different (and sometimes worse) code than a structured spec, mostly on SQL and Bash. That gap is what you actually get day to day.
16. **More thinking is not always better.** `xhigh` rescued tasks that `low` failed, but also broke at least one that `low` passed, at 5 to 10 times the tokens and minutes per answer.
17. **Measure from the engine, not only the API.** Strata's log gives true generation speed, prefix reuse, draft acceptance and the expert-cache hit rate per request. Wall time alone mixes all of those together.
