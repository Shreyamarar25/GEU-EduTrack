"""
Process synchronization demos with real threads.

  race_demo()          shared counter updated by several threads - with and without a MUTEX
  producer_consumer()  bounded buffer (the report-request queue): producers = users asking for reports,
                       consumers = the scheduler approving them. Uses 2 SEMAPHORES + 1 MUTEX.
"""
import collections
import random
import threading
import time


def race_demo(workers=4, increments=200, use_mutex=False):
    counter = {"value": 0}
    lock = threading.Lock()  # the mutex

    def work():
        for _ in range(increments):
            if use_mutex:
                with lock:                       # only one thread inside at a time
                    v = counter["value"]
                    time.sleep(0.0001)           # forces a thread switch in the middle of read-modify-write
                    counter["value"] = v + 1
            else:
                v = counter["value"]             # read
                time.sleep(0.0001)               # another thread can sneak in here
                counter["value"] = v + 1         # write back a stale value

    threads = [threading.Thread(target=work) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    expected = workers * increments
    actual = counter["value"]
    return {"use_mutex": use_mutex, "workers": workers, "increments_each": increments,
            "expected": expected, "actual": actual, "lost_updates": expected - actual,
            "correct": actual == expected}


def producer_consumer(producers=2, consumers=1, items=4, capacity=3):
    buffer = collections.deque()
    empty = threading.Semaphore(capacity)   # counts FREE slots  (producer waits when 0)
    full = threading.Semaphore(0)           # counts FILLED slots (consumer waits when 0)
    mutex = threading.Lock()                # one thread touches the buffer at a time
    log_lock = threading.Lock()
    log, stats = [], {"max_size": 0, "produced": 0, "consumed": 0}

    def note(actor, action, item):
        with log_lock:
            log.append({"step": len(log) + 1, "actor": actor, "action": action, "item": item,
                        "buffer": list(buffer), "size": len(buffer)})

    def producer(pid):
        for k in range(1, items + 1):
            item = f"U{pid}-Request{k}"
            time.sleep(random.uniform(0.001, 0.004))
            empty.acquire()                              # wait for a free slot
            with mutex:                                  # enter critical section
                buffer.append(item)
                stats["produced"] += 1
                stats["max_size"] = max(stats["max_size"], len(buffer))
                note(f"Producer {pid}", "ADD", item)
            full.release()                               # signal: one more item available

    def consumer(cid, share):
        for _ in range(share):
            full.acquire()                               # wait for an item
            with mutex:
                item = buffer.popleft()
                stats["consumed"] += 1
                note(f"Scheduler {cid}", "APPROVE", item)
            empty.release()                              # signal: one more free slot
            time.sleep(random.uniform(0.002, 0.006))

    total = producers * items
    base, extra = divmod(total, consumers)
    threads = [threading.Thread(target=producer, args=(p + 1,)) for p in range(producers)]
    threads += [threading.Thread(target=consumer, args=(c + 1, base + (1 if c < extra else 0)))
                for c in range(consumers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    stuck = any(t.is_alive() for t in threads)
    return {"capacity": capacity, "producers": producers, "consumers": consumers, "items_each": items,
            "produced": stats["produced"], "consumed": stats["consumed"],
            "max_buffer_size": stats["max_size"], "never_overflowed": stats["max_size"] <= capacity,
            "completed": not stuck and stats["consumed"] == total, "log": log}