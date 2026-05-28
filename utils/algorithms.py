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
