def run_fifo(processes):
    """
    FIFO (First-In, First-Out) - Non-preemptive.
    Processes run in arrival order.
    No context switch overhead.
    """
    procs = sorted(processes, key=lambda p: (p["arrival"], p["id"]))  # tiebreaker by id
    timeline = []   # list of (pid, start, end, type)
    time = 0

    for p in procs:
        if time < p["arrival"]:
            time = p["arrival"]
        start = time
        end = time + p["burst"]
        timeline.append({"pid": p["id"], "start": start, "end": end, "type": "running"})
        time = end

    return timeline


def run_sjf(processes):
    """
    SJF (Shortest Job First) - Non-preemptive.
    At each decision point, pick the shortest available job.
    No context-switch overhead.
    """
    unstarted = processes.copy()
    timeline = []
    time = 0

    while unstarted:
        available = [p for p in unstarted if p["arrival"] <= time]
        if not available:  # CPU idle
            # Advance to next arrival
            time = min(p["arrival"] for p in unstarted)
            continue
        # Pick shortest burst, tiebreaker by arrival and ID
        chosen = min(available, key=lambda p: (p["burst"], p["arrival"], p["id"]))
        start = time
        end = time + chosen["burst"]
        timeline.append({"pid": chosen["id"], "start": start, "end": end, "type": "running"})
        time = end
        unstarted.remove(chosen)

    return timeline


def run_round_robin(processes, quantum, overhead):
    """
    Round-Robin - Preemptive.
    Context switch overhead (save+load) applies whenever a process is INTERRUPTED
    mid-burst (i.e. it consumed a full quantum but still has remaining burst time).
    This applies regardless of whether the next process to run is the same or a
    different one.
    No overhead is generated when a process finishes naturally (nothing to save).
    """
    # Generates a list of unstarted processes, with 'remaining' key, and sorted by arrival
    unstarted = sorted(
        [dict(p, remaining=p["burst"]) for p in processes], 
        key=lambda p: (p["arrival"], p["id"])
    )
    timeline = []
    time = 0
    queue = []  # queue of processes

    # Move processes from unstarted to queue when they arrive
    def check_arrivals(t):
        while unstarted and unstarted[0]["arrival"] <= t:
            queue.append(unstarted.pop(0))  # remove from unstarted and add to queue

    check_arrivals(time)

    while queue or unstarted:
        if not queue:  # CPU idle until next arrival
            time = unstarted[0]["arrival"]
            check_arrivals(time)
            continue

        # Takes the first process in the queue to run
        current = queue.pop(0)
        run_time = min(quantum, current["remaining"])
        timeline.append({"pid": current["id"], "start": time, "end": time + run_time, "type": "running"})
        time += run_time
        current["remaining"] -= run_time

        # Process was interrupted mid-burst -> pay overhead
        if current["remaining"] > 0:
            time += overhead
            timeline.append({"pid": current["id"], "start": time - overhead, "end": time, "type": "overhead"})
            check_arrivals(time)  # check new arrivals during overhead time before re-queuing
            queue.append(current)
        else:
            check_arrivals(time)

    return timeline


def run_priority(processes, quantum, overhead):
    """
    Priority Scheduling - Preemptive.
    Lower priority number = higher priority.
    At each quantum, the highest-priority ready process runs.
    Context switch overhead with same rules as RR.
    """
    unstarted = sorted(
        [dict(p, remaining=p["burst"]) for p in processes], 
        key=lambda p: (p["arrival"], p["id"])
    )
    timeline = []
    time = 0
    queue = []

    def check_arrivals(t):
        while unstarted and unstarted[0]["arrival"] <= t:
            queue.append(unstarted.pop(0))

    check_arrivals(time)

    while queue or unstarted:
        if not queue:
            time = unstarted[0]["arrival"]
            check_arrivals(time)
            continue

        # Choose the highest priority process (lowest number), tiebreaker by arrival and ID
        chosen = min(queue, key=lambda p: (p["priority"], p["arrival"], p["id"]))
        run_time = min(quantum, chosen["remaining"])
        timeline.append({"pid": chosen["id"], "start": time, "end": time + run_time, "type": "running"})
        time += run_time
        chosen["remaining"] -= run_time

        check_arrivals(time)

        # Process was interrupted mid-burst -> pay overhead
        if chosen["remaining"] > 0:
            time += overhead
            timeline.append({"pid": chosen["id"], "start": time - overhead, "end": time, "type": "overhead"})
            check_arrivals(time)
        else:  # if finished, remove from queue and don't charge overhead
            queue.remove(chosen)

    return timeline

def run_edf(processes, quantum, overhead):
    """
    EDF (Earliest Deadline First) - Preemptive.
    At each quantum, run the ready process with the earliest absolute deadline.
    Context switch overhead with same rules as RR.
    """
    unstarted = sorted(
        [dict(p, remaining=p["burst"]) for p in processes], 
        key=lambda p: (p["arrival"], p["id"])
    )
    timeline = []
    time = 0
    queue = []

    def check_arrivals(t):
        while unstarted and unstarted[0]["arrival"] <= t:
            queue.append(unstarted.pop(0))

    check_arrivals(time)

    while queue or unstarted:
        if not queue:
            time = unstarted[0]["arrival"]
            check_arrivals(time)
            continue
        
        # Choose the process with the earliest deadline, tiebreaker by arrival and ID
        chosen = min(queue, key=lambda p: (p["deadline"], p["arrival"], p["id"]))
        # If deadline is relative, we need to calculate absolute deadline as arrival+deadline
        # chosen = min(queue, key=lambda p: (p["arrival"] + p["deadline"], p["arrival"], p["id"]))
        run_time = min(quantum, chosen["remaining"])
        timeline.append({"pid": chosen["id"], "start": time, "end": time + run_time, "type": "running"})
        time += run_time
        chosen["remaining"] -= run_time

        check_arrivals(time)

        if chosen["remaining"] > 0:
            time += overhead
            timeline.append({"pid": chosen["id"], "start": time - overhead, "end": time, "type": "overhead"})
            check_arrivals(time)
        else:  # if finished, remove from queue and don't charge overhead
            queue.remove(chosen)
    
    return timeline


def run_cfs(processes, overhead):
    """
    CFS-Sim (Completely Fair Scheduler, simplified) - Preemptive.
 
    Each process tracks a virtual runtime (vruntime) that grows proportionally
    to real time and priority weight:
        vruntime += Δt * w(priority) 
        w(priority) = 1.25 ^ (priority - 1)
    Rules:
      - On arrival, vruntime is set to the current time
      - At each step, the process with the minimum vruntime runs
      - The time slice (delta_t) is calculated based on the minimum between the
        remaining burst time and granular slice. Granular slice is the time required
        for the current process vrtutime to match the vruntime of the next process
        in the queue
      - The time slice (delta_t) is the minimum between remaining burst and the
        granular slice. Granular slice is the time for the current process's vruntime 
        to catch up to the next process's vruntime [(next_vruntime-current_vruntime)/w]
      - Preemption occurs when another process's vruntime is shorter than the
        currently running process's vruntime
      - Overhead applies only on an actual process switch (interrupted process
        is displaced by a DIFFERENT process). If the same process remains
        the minimum after its slice, it continues without overhead
      - Lower priority number -> lower weight -> slower vruntime growth -> more CPU
        time (consistent with the other algorithms where 1 = most important)
    """
    unstarted = sorted(
        [dict(p, remaining=p["burst"], vruntime=0.0) for p in processes],
        key=lambda p: (p["arrival"], p["id"])
    )
    timeline = []
    time = 0
    ready = []  # processes currently available to run
    min_granularity = 1.0  # minimum time slice to prevent starvation
    last_pid = None
    last_was_interrupted = False
 
    def check_arrivals(t):
        # Newly arrived processes enter with vruntime = current time
        while unstarted and unstarted[0]["arrival"] <= t:
            p = unstarted.pop(0)
            p["vruntime"] = float(t)
            ready.append(p)
 
    check_arrivals(time)
 
    while ready or unstarted:
        if not ready:  # CPU idle: jump to next arrival
            time = unstarted[0]["arrival"]
            check_arrivals(time)
            last_pid = None
            last_was_interrupted = False
            continue
 
        # Always pick the process with the smallest vruntime
        current = min(ready, key=lambda p: (p["vruntime"], p["arrival"], p["id"]))
 
        # Overhead fires only when the process actually changes
        if last_was_interrupted and current["id"] != last_pid:
            timeline.append({"pid": last_pid, "start": time, "end": time + overhead, "type": "overhead"})
            time += overhead
            check_arrivals(time)
            if not ready:
                last_pid = None
                last_was_interrupted = False
                continue
            current = min(ready, key=lambda p: (p["vruntime"], p["arrival"], p["id"]))
 
        w = 1.25 ** (current["priority"] - 1)
 
        # Compute how long current process can run (delta_t) -> minimum between remaining and granular slice
        remaining = current["remaining"]
        if len(ready) > 1:  # calculate granular slice
            next_vruntime = min(p["vruntime"] for p in ready if p["id"] != current["id"])
            granular_slice = (next_vruntime - current["vruntime"]) / w
            delta_t = min(remaining, granular_slice)
        else:
            delta_t = remaining
        delta_t = max(min_granularity, delta_t)  # enforce minimum granularity
        # Bound by next arrival so new processes can immediately preempt
        if unstarted:
            time_to_next = unstarted[0]["arrival"] - time
            if time_to_next > 0:
                delta_t = min(delta_t, time_to_next)
        delta_t = min(delta_t, remaining)
        
        timeline.append({"pid": current["id"], "start": time, "end": time + delta_t, "type": "running"})
        time += delta_t
        current["remaining"] -= delta_t
        current["vruntime"] += delta_t * w
 
        check_arrivals(time)
 
        if current["remaining"] > 0:
            last_pid = current["id"]
            last_was_interrupted = True
        else:
            ready.remove(current)
            last_pid = current["id"]
            last_was_interrupted = False
 
    return timeline


def run_dwarr(processes, overhead):
    """
    DWARR — Deadline-Weighted Adaptive Round-Robin (custom algorithm).

    Combines EDF selection with a dynamic quantum that emerges from the deadline
    gap between the current process and the next most urgent one.
    - Selection: always pick the earliest deadline. Among equal deadlines, a
    dispatch_count tiebreaker rotates through processes in round-robin fashion.
    - Dynamic quantum:
        quantum = max(1, min(remaining, next.deadline - current.deadline))
        - Large gap  -> long uninterrupted run (process is far more urgent)
        - Small gap  -> short quantum (fair sharing among close deadlines)
        - Gap = 0    -> quantum = 1 (pure RR rotation)
        - Alone      -> run to completion
    - The slice is also bounded by the next arrival time.
    - Overhead only on an actual process switch (same as CFS).
    """
    unstarted = sorted(
        [dict(p, remaining=p["burst"]) for p in processes],
        key=lambda p: (p["arrival"], p["id"])
    )
    timeline = []
    time = 0
    queue = []
    last_pid = None
    last_was_interrupted = False
    dispatch_count = {p["id"]: 0 for p in processes}

    def check_arrivals(t):
        while unstarted and unstarted[0]["arrival"] <= t:
            queue.append(unstarted.pop(0))

    check_arrivals(0)

    while queue or unstarted:
        if not queue:
            time = unstarted[0]["arrival"]
            check_arrivals(time)
            last_pid = None
            last_was_interrupted = False
            continue

        chosen = min(queue, key=lambda p: (p["deadline"], dispatch_count[p["id"]], p["arrival"], p["id"]))

        if last_was_interrupted and chosen["id"] != last_pid:
            timeline.append({"pid": last_pid, "start": time, "end": time + overhead, "type": "overhead"})
            time += overhead
            check_arrivals(time)
            if not queue:
                last_pid = None
                last_was_interrupted = False
                continue
            chosen = min(queue, key=lambda p: (p["deadline"], dispatch_count[p["id"]], p["arrival"], p["id"]))

        others = [p for p in queue if p["id"] != chosen["id"]]
        if not others:
            quantum = chosen["remaining"]
        else:
            next_proc = min(others, key=lambda p: (p["deadline"], p["arrival"], p["id"]))
            deadline_gap = next_proc["deadline"] - chosen["deadline"]
            quantum = max(1, min(chosen["remaining"], deadline_gap))

        if unstarted:
            time_to_next = unstarted[0]["arrival"] - time
            if time_to_next > 0:
                quantum = min(quantum, time_to_next)

        quantum = max(1, int(quantum))
        quantum = min(quantum, chosen["remaining"])

        dispatch_count[chosen["id"]] += 1
        timeline.append({"pid": chosen["id"], "start": time, "end": time + quantum, "type": "running"})
        time += quantum
        chosen["remaining"] -= quantum
        check_arrivals(time)

        if chosen["remaining"] > 0:
            last_pid = chosen["id"]
            last_was_interrupted = True
        else:
            queue.remove(chosen)
            last_pid = chosen["id"]
            last_was_interrupted = False

    return timeline
