from tqdm import tqdm
import numpy as np

from simulation import WRPSimulation

def confidence_interval(values, z=1.96):
    """
    Compute sample mean and 95% confidence interval half-width.
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)

    mean = np.mean(arr)

    std = np.std(arr, ddof=1)
    half_width = z * std / np.sqrt(n)
    return mean, half_width


def run_replications(n_replications=30, arrival_multiplier=1.0, show_progress=True):
    """
    Run multiple independent replications of the WRP simulation.
    """
    system_times = []
    entrance_waits = []
    blocked_fractions = []

    station_mean_queue = {}
    station_mean_occupancy = {}
    station_mean_wait = {}
    station_nr_arrivals = {}

    iterator = range(n_replications)
    if show_progress:
        iterator = tqdm(
            iterator,
            desc=f"WRP replications (x{arrival_multiplier:.2f} arrivals)",
            ncols=100
        )

    for rep in iterator:
        sim = WRPSimulation(
            seed=1000 + rep,
            arrival_multiplier=arrival_multiplier
        )
        results = sim.run()

        system_times.append(results.mean_system_time)
        entrance_waits.append(results.mean_entrance_wait)
        blocked_fractions.append(results.fraction_road_blocked)

        for station, value in results.station_mean_queue.items():
            station_mean_queue.setdefault(station, []).append(value)

        for station, value in results.station_mean_occupancy.items():
            station_mean_occupancy.setdefault(station, []).append(value)

        for station, value in results.station_mean_wait.items():
            station_mean_wait.setdefault(station, []).append(value)

        for station, value in results.station_nr_arrivals.items():
            station_nr_arrivals.setdefault(station, []).append(value)

    summary = {
        "mean_system_time": confidence_interval(system_times),
        "mean_entrance_wait": confidence_interval(entrance_waits),
        "fraction_road_blocked": confidence_interval(blocked_fractions),
        "station_mean_queue": {
            station: confidence_interval(values)
            for station, values in station_mean_queue.items()
        },
        "station_mean_occupancy": {
            station: confidence_interval(values)
            for station, values in station_mean_occupancy.items()
        },
        "station_mean_wait": {
            station: confidence_interval(values)
            for station, values in station_mean_wait.items()
        },
        "station_nr_arrivals": {
            station: confidence_interval(values)
            for station, values in station_nr_arrivals.items()
        },
        "raw": {
            "system_times": system_times,
            "entrance_waits": entrance_waits,
            "blocked_fractions": blocked_fractions,
            "station_mean_queue": station_mean_queue,
            "station_mean_occupancy": station_mean_occupancy,
            "station_mean_wait": station_mean_wait,
            "station_nr_arrivals": station_nr_arrivals,
        },
    }

    return summary


def print_summary(title, summary):
    """
    Print results in a clean format.
    """
    mst_mean, mst_hw = summary["mean_system_time"]
    mew_mean, mew_hw = summary["mean_entrance_wait"]
    blk_mean, blk_hw = summary["fraction_road_blocked"]

    print(f"\n{title}")
    print("-" * len(title))
    print(f"Mean system time      : {mst_mean:.2f} ± {mst_hw:.2f} sec")
    print(f"Mean entrance waiting : {mew_mean:.2f} ± {mew_hw:.2f} sec")
    print(f"Road blocked fraction : {blk_mean:.4f} ± {blk_hw:.4f}")

    print("\nStation mean queue")
    for station, (mean, hw) in summary["station_mean_queue"].items():
        print(f"  {station}: {mean:.2f} ± {hw:.2f}")

    print("\nStation mean occupancy")
    for station, (mean, hw) in summary["station_mean_occupancy"].items():
        print(f"  {station}: {mean:.2f} ± {hw:.2f}")

    print("\nStation mean wait")
    for station, (mean, hw) in summary["station_mean_wait"].items():
        print(f"  {station}: {mean:.2f} ± {hw:.2f} sec")

    print("\nStation arrivals")
    for station, (mean, hw) in summary["station_nr_arrivals"].items():
        print(f"  {station}: {mean:.2f} ± {hw:.2f}")

def main():
    n_replications = 300

    # Base case
    base_summary = run_replications(
        n_replications=n_replications,
        arrival_multiplier=1.0,
        show_progress=True
    )
    print_summary("Base case", base_summary)

    # Scenario: 20% more arrivals
    plus20_summary = run_replications(
        n_replications=n_replications,
        arrival_multiplier=1.2,
        show_progress=True
    )
    print_summary("20% more arrivals", plus20_summary)


if __name__ == "__main__":
    main()