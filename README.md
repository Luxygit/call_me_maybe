*This project has been created as part of the 42 curriculum by dievarga*

# Fly-in

## Description

Fly-in is an object oriented Python simulation project that controls
the routing of a drone fleet across a connected map graph. 
The program reads and parses map configuration files, finds an optimised path,
validates occupancy limits and implements a turn-by-turn interactive sim
from the start zone to the end zone.
In case zone colours are defined in the map file, there is a visual output via
pygame, otherwise the output is only text on the terminal.

## Instructions

### Makefile targets

- make install      : create the virtual environment and install dependencies
- make run          : run the project with a map file
- make debug        : run the project under pdb pythons debugger
- make clean        : remove caches and temp files
- make lint         : run flake8 and mypy
- make lint-strict  : execute the commands flake8 . and mypy . --strict

### Installation

make install - creates .venv and installs pygame visual graphic output.

### Debugging
Using make debug' we got access to pythons debugger to examine the program:
- n (Next): Executes the current line and moves to the next line
- s (Step): Steps inside a function call
- c (Continue): Lets the program run normally until it hits a crash or finishes
- p <variable> (Print): Displays the live contents of any variable
- l (List): Prints the surrounding lines of code
- q (Quit): Instantly terminates the debugger

### Execution

make run - executes program and it also installs dependencies if missing.

Common erros such as missing files, invalid paths, file permit errors,
duplicates, among others specified by the subject are handled via 
'MapParseError' and output is sent through 'sys.stderr' and exits the
progam with a code '1'. Keyboard interrupts are also handled.

For the visual window output 2 keybindings are defined, SPACEBAR, to 
advance the simulation 1 turn, starting in turn 0, and ESCAPE, to close the
window. If no drones move during a turn then an empty line is printed.

If no colours are specified in the map file for the zones, then the output is
only shown as terminal text following the subject specified format 

## Resources

- PygameCE YouTube tutorials
- GeekForGeeks "Time and space complexity of Dijkstra's algorithm"

### AI usage

AI (Claude & Gemini) were used to:
- Debug the code (mostly typos, parsing and path logic issues)
- Understand the Dijkstra algorithm logic and implementation
- Understand PygameCE visual library documentation

### PygameCE

The graphic visualizer uses a fixed window dimension of 1400x800 pixels to
simplify the coordinate positioning of the objects and also to make sure
a reasonable number of objects fit in the screen comfortably.
Objects represented visually: zones, zone capacity, drones, connection,
connection capacity, sim turn counter and finished simulation notice.

Colours from map files are taken by 'pygame.Colors' list or in case only
some colours are missing then they fallback to default 'white'.

Text is displayed with a border outline for clarity, for which a 4 way
offset was used.

## Algorithm

### Graph Construction

The whole map network is made inside a 'Graph' class structure using a 
bidirectional list dictionary 'self.adj_list'.
Zone properties are parsed from raw text lines into 'Zones' and also
'Connection' data objects allowing to monitor occupancy and capacity.

### Dijkstra's algorithm

Before a single drone leaves the starting point, the `Router` class
calculates the most efficient route across the network graph using
Dijkstra's Algorithm.
To implemente this pathfinding algorithm efficiently, python's heapq
min-heap module was used to instantly extract the next cheapest zone to 
explore with a highly optimized time complexity.

Since an unweighted path choice would have miscalculated complex paths,
dead ends and loops, this pathfinder uses integers as weights given according
to the zone properties. 
- 'blocked' Zones are immediately ignored by the loop.
- 'restricted' Zones are evaluated with a int cost of 4
- 'normal' Zones are evaluated with a baseline int cost of 2
- 'priority' Zones are evaluated with a slightly minor int cost of 1

## 2. Step-by-Turn Engine & Look-Ahead Capacity Logic

Every time you press the SPACEBAR or advance the simulation, the engine runs a 
discrete turn. Each turn execution is divided into two separate phases that run 
one after another:

- Phase A: The Arrival Phase (`_process_arrivals`)
First, the engine checks all drones that are currently flying inside connections 
toward restricted zones. 
* Their transit countdowns drop by 1.
* If a countdown reaches 0, the drone officially "lands" in its destination zone.
* The moment it lands, it increments that zone's drone counter and immediately
calls `connection.leave_path()`. This instantly frees up the link capacity of 
that connection for the current turn.
* Drones that land this turn are added to a temporary `moved_this_turn` set so 
they are blocked from taking off again on the exact same turn loop iteration.

- Phase B: The Launch Phase (`_route_resting_drones`)
Next, the engine loops through all resting drones to decide if they can take off.
To maximize fleet throughput without causing jams, it uses a sequential 
tracking system:
1. Path Check: The drone asks the Dijkstra router for the next zone on its 
pre-calculated shortest path to the goal.
2. Snapshot Isolation: At the start of the launch phase, we take a clean 
dictionary snapshot of the current zone counts (`current_zone_count`) and link 
capacities (`current_conn_count`).
3. Capacity Validation & Look-Ahead:
   * Connection Link Capacity: The engine checks if the upcoming connection 
   has reached its `max_link_capacity`. If we add our turn's look-ahead 
   reservations and it's full, the drone waits.
   * Target Zone Capacity: For immediate movements (Normal/Priority hubs), it 
   checks if the target zone is full. If it is restricted, we skip this zone 
   check because the drone won't land until a later turn when the zone is clear.
4. Takeoff & Instant Departure Release: Once a drone is cleared to take off,
it releases its current zone. We instantly decrement `current_zone_count[og_zone]`
right inside the loop. This means as soon as a drone moves forward, the drone
evaluated next in the exact same turn loop will immediately see that a slot 
opened up and can move in to occupy it.
5. **Reservation Maps:** To avoid double-counting a drone's transit before
the turn finishes, we store all newly planned movements inside `reserved_spots`
and `reserved_conn` tracking maps instead of modifying the global base counts
mid-loop.

### Performance & Complexity Answers

* **How efficient is your algorithm?**
It is highly efficient because it manages capacities dynamically in memory.
By combining strict priority rules with an instant queue-release mechanism
inside the loop, drones follow each other perfectly nose-to-tail down
bottlenecks without wasting single empty turns.

* **Can it work with a large number of drones?**
Yes. Because the scheduling engine processes drones sequentially in a flat
list loop (`for drone in self.drones`), processing scales linearly with the
size of the fleet. Drones cleanly queue behind each other in memory arrays
when bottleneck capacity thresholds are hit. It handles large fleets easily.

* **What is the complexity (e.g., O(n), O(log n), etc.)?**
The pathfinding operations run at O((V + E) \log V) complexity, where V 
is the number of zones (vertices) and E is the number of connections (edges).
The min-heap ensures that finding the next closest zone only takes logarithmic
time O(\log V). The simulation scheduling loop runs at O(D.P) per turn,
where D is the total number of drones and P is the path length.

* **Are you recalculating or caching paths?**
Right now, the algorithm queries the static router path on every turn to
check its next step. Because the graph network is completely static and the map
does not change mid-simulation, the paths do not shift. Because our Dijkstra
implementation is extremely lightweight and fast, running it per turn causes
zero performance lag on standard maps.

* **How does it impact memory usage?**
The memory impact is small and lightweight. The graph structure is 
stored using native Python objects, tiny reference dictionaries, and integer counters. Memory consumption remains stable and completely flat throughout the
runtime of the simulation loop, preventing any risk of leaks.
