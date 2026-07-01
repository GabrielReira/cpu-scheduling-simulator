# CPU Scheduling Simulator

[![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg)](README.pt.md)

An interactive CPU scheduling simulator built with Python and Dash, featuring animated Gantt charts and detailed performance metrics for 7 scheduling algorithms: FIFO, SJF, Round-Robin, Priority, EDF, CFS, and DWARR (custom).

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Dash](https://img.shields.io/badge/Dash-2.x-008DE4?style=flat&logo=plotly&logoColor=white)](https://dash.plotly.com/)
[![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75?style=flat&logo=plotly&logoColor=white)](https://plotly.com/)

---

## :computer: About

This simulator models a CPU executing a set of user-defined processes under seven different scheduling algorithms. The goal is to make it visual and numerical how each algorithm distributes CPU time among processes.

<p align="center">
  <img src=".github/interface.gif" width="90%">
</p>

The simulator assumes:
- **Single-core CPU**: only one process runs at a time
- **Priority 1 = most important**: the lower the number, the higher the priority
- **Deadlines are absolute**: they refer to the point in time by which the process must finish, not a relative offset

### How to use

The user provides, for each process:
- **ID**: process identifier (optional; defaults to P1, P2, P3…)
- **Arrival**: time at which the process enters the ready queue (optional; defaults to 0)
- **Burst**: total CPU time required (required)
- **Priority**: required only for Priority Scheduling and CFS
- **Deadline**: required only for EDF and DWARR

For preemptive algorithms, the user also provides:
- **Quantum**: maximum duration of each CPU slice
- **Overhead**: context-switch cost (save + load)

After filling in the processes, simply click the desired algorithm button:

| Button | Algorithm | Type |
|---|---|---|
| FIFO | First-In, First-Out | Non-preemptive |
| SJF | Shortest Job First | Non-preemptive |
| RR | Round-Robin | Preemptive |
| Priority | Priority Scheduling | Preemptive |
| EDF | Earliest Deadline First | Preemptive |
| CFS | Completely Fair Scheduler | Preemptive |
| DWARR | Deadline-Weighted Adaptive Round-Robin | Preemptive |

The result is displayed immediately: the animated Gantt chart and metrics table appear on the right.

### Gantt Chart

The Gantt chart is **animated** and **time-driven**. Each frame corresponds to one tick on the time axis (t = 0, 1, 2, ..., total time). As the animation plays, bars grow from left to right, showing exactly how the scheduler fills each time unit — all bars advance simultaneously.

| Color | Meaning |
|---|---|
| :green_square: Green | Process running (within deadline) |
| :yellow_square: Yellow | Process waiting (arrived but not on CPU) |
| :red_square: Red | Context-switch overhead (shown only on the interrupted process's row) |
| :white_large_square: Gray | Process running after its deadline has passed |

Available controls:
- **▶ Play**: replays the animation from the beginning (t = 0)
- **⏸ Pause**: freezes the animation at the current frame
- **Slider**: drag to any point in time manually

### Metrics

| Column | Description |
|---|---|
| **Arrival** | Time at which the process arrives |
| **Burst** | Total CPU time required by the process |
| **Deadline** | Time by which the process must finish (when applicable) |
| **Priority** | Priority value (when applicable) |
| **Start** | First moment the process actually ran on CPU |
| **Finish** | Last moment the process finished running |
| **Waiting** | `Turnaround − Burst`: time spent not executing its own burst |
| **Turnaround** | `Finish − Arrival`: total time from arrival to completion |
| **Deadline OK?** | ✓ if finished at or before its deadline, ✗ otherwise |

Below the table, the **Average Turnaround** is displayed — the mean turnaround across all processes, the primary figure of merit for comparing algorithms.

> **Note on waiting time:** includes both idle waiting (CPU busy with other processes) and the process's own context-switch overhead periods. It represents all time the process was alive but not executing its own burst.

---

## :hammer_and_wrench: Built With

- **[Python 3.10+](https://www.python.org/)**: core language
- **[Dash 2.x](https://dash.plotly.com/)**: interactive web application framework
- **[Plotly 5.x](https://plotly.com/python/)**: animated and interactive Gantt charts
- **[Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)**: UI layout and styling

---

## :rocket: Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/GabrielReira/cpu-scheduling-simulator.git
cd cpu-scheduling-simulator

# 2. Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

Then open your browser at `http://127.0.0.1:8050`.

### Project Structure

```
cpu-scheduling-simulator/
├── app.py                   # Dash application, layout and callbacks
├── requirements.txt
└── utils/
    ├── algorithms.py        # Implementation of all 7 scheduling algorithms
    ├── metrics_and_gantt.py # Metrics computation and animated Gantt chart
    └── style.py             # Color palette and UI style constants
```

---

## :gear: Algorithms

The simulator implements seven algorithms divided into two categories: non-preemptive and preemptive.

### Non-preemptive

#### FIFO: First-In First-Out
The simplest policy. Processes are executed in order of arrival. Once started, a process runs to completion without interruption.

#### SJF: Shortest Job First
At each scheduling decision point, the algorithm selects the ready process with the shortest burst time. Ties are broken by arrival time. Like FIFO, it is non-preemptive: the chosen process runs to completion.

### Preemptive

All preemptive algorithms use the **Quantum** and **Overhead** parameters. The overhead rule is described in the [Scheduling Rules](#scheduling-rules) section.

#### RR: Round-Robin
Processes take turns on the CPU in arrival order. Each process runs for at most one quantum of CPU time. If it does not finish, it is placed back at the end of the queue and the next process takes over. Uses a fixed quantum.

#### Priority: Priority Scheduling
At each quantum, the most important process (lowest priority number) is selected. If the same process remains the most important after its quantum, it continues without overhead.

#### EDF: Earliest Deadline First
At each quantum, the ready process with the earliest absolute deadline is selected. Like Priority scheduling, overhead is only charged when the running process changes.

#### CFS: Completely Fair Scheduler _(simplified)_
Inspired by the Linux kernel's CFS. Each process maintains a **virtual runtime** (`vruntime`) that accumulates proportionally to real execution time and priority weight:

```
vruntime += Δt × w(priority)
w(priority) = 1.25 ^ (priority − 1)
```

At each step, the process with the **lowest vruntime** runs. On arrival, a process's vruntime is set to the current time (fair entry). The slice size is computed as the time needed for the current process's vruntime to reach the next process's — no fixed quantum. A lower priority number means a lower weight, meaning vruntime grows more slowly, resulting in more CPU time.

Overhead is only charged when the running process changes.

#### DWARR: Deadline-Weighted Adaptive Round-Robin _(custom algorithm)_
An original algorithm designed for this simulator. Combines EDF urgency with round-robin fairness and a dynamic quantum. Three rules govern each scheduling decision:

1. **Urgency band**: Find the most urgent process in the queue (earliest deadline). Its remaining burst defines a window `W`. All processes whose deadline falls within `W` of the earliest deadline form the **urgency band** and are considered comparably urgent:
   ```
   band = { process : process.deadline − earliest.deadline ≤ W }
   ```
   Processes outside the band wait — they are not yet time-critical.

2. **Selection**: Within the band, select the least-recently-dispatched process (round-robin rotation via dispatch counter). This prevents any process from monopolizing the CPU when several are comparably urgent.

3. **Dynamic quantum**: Computed as the deadline gap to the nearest competitor inside the band:
   ```
   quantum = min(remaining_burst, nearest_deadline_gap)
   ```
   | Situation | Gap | Quantum |
   |---|---|---|
   | Alone in band | — | `remaining` (runs to completion) |
   | Equal deadlines | 0 | 1 (Round-Robin) |
   | Deadlines 1 apart | 1 | 1 (fine interleaving) |
   | Deadlines 3 apart | 3 | 3 (medium slices) |
   | Deadlines 4 apart, burst 4 | 4 | 4 (runs to completion) |

The window `W` shrinks as the most urgent process executes, naturally tightening the band over time and giving increasing priority to whoever is closest to their deadline. Overhead only when a process switch takes place.

---

## :bar_chart: Examples

### Example 1

| ID | Arrival | Burst | Priority | Deadline |
|---|---|---|---|---|
| P1 | 0 | 5 | 3 | 15 |
| P2 | 3 | 4 | 2 | 20 |
| P3 | 2 | 7 | 1 | 21 |

Parameters: **Quantum = 2**, **Overhead = 1**

| Algorithm | Average Turnaround |
|---|---|
| FIFO | 9.33 |
| SJF | 8.33 |
| RR | 17.33 |
| Priority | 16.00 |
| EDF | 12.00 |
| CFS | 22.67 |
| DWARR | 13.33 |

### Example 2

| ID | Arrival | Burst | Priority | Deadline |
|---|---|---|---|---|
| A | 0 | 14 | 4 | 28 |
| B | 0 | 4 | 1 | 6 |
| C | 0 | 2 | 3 | 8 |
| D | 0 | 6 | 5 | 13 |
| E | 0 | 8 | 2 | 37 |

Parameters: **Quantum = 4**, **Overhead = 1**

| Algorithm | Average Turnaround |
|---|---|
| FIFO | 22.40 |
| SJF | 14.80 |
| RR | 23.80 |
| Priority | 20.60 |
| EDF | 18.40 |
| CFS | 37.80 |
| DWARR | 17.40 |

### Example 3

| ID | Arrival | Burst | Priority | Deadline |
|---|---|---|---|---|
| A | 0 | 4 | 1 | 7 |
| B | 2 | 2 | 2 | 5 |
| C | 4 | 1 | 3 | 8 |
| D | 6 | 3 | 4 | 10 |

Parameters: **Quantum = 2**, **Overhead = 1**

| Algorithm | Average Turnaround |
|---|---|
| FIFO | 3.75 |
| SJF | 3.50 |
| RR | 5.00 |
| EDF | 5.00 |
| CFS | 6.00 |
| DWARR | 4.50 |

---

## :clipboard: Scheduling Rules

These rules apply to all preemptive algorithms.

### Context-Switch Overhead
Context-switch overhead (the cost of saving and restoring CPU state) is modeled as a **save + load** operation. It is charged only when both halves occur:

- **No overhead when a process finishes naturally**: a process that completes its burst has nothing to save. The next process is simply loaded (only a *load*, not a *save+load*)
- **Overhead is charged when a running process is interrupted**: when a process still has remaining burst and a different process takes over the CPU. This represents a full save+load
> - **Round-Robin exception**: overhead is charged whenever a process is interrupted, regardless of whether the next process is the same or different. This reflects the fact that the interrupted process is re-queued and its state must be saved and reloaded on its next turn

### Preemption
Preemption occurs at quantum boundaries or when a new process arrives. After either event, the scheduler re-evaluates the ready queue and may switch processes.

### Queue Order During Overhead
If a new process arrives during the overhead period, it is enqueued **before** the interrupted process is re-queued. This means newly arrived processes run before the process that was just preempted.

---

## :scroll: License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<p align="center"><strong>By <a href="https://www.linkedin.com/in/gabrielreira/">Gabriel</a></strong></p>
