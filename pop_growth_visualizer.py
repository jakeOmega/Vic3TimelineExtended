import numpy as np
import matplotlib.pyplot as plt

# Pop Growth Constants
min_birthrate = 0.00080 * 12
max_birthrate = 0.00475 * 12
min_mortality = 0.00100 * 12
max_mortality = 0.00600 * 12

pop_growth_equilibrium_sol = 4
pop_growth_transition_sol = 11
pop_growth_max_sol = 18
pop_growth_stable_sol = 35

transition_birthrate_mult = 1
max_growth_mortality_mult = 0.4

# Derived Values
birthrate_at_transition = max_birthrate * transition_birthrate_mult
rate_at_equilibrium = (
    pop_growth_equilibrium_sol
    * ((birthrate_at_transition - max_birthrate) / pop_growth_transition_sol)
    + max_birthrate
)

mortality_starving_slope = (
    rate_at_equilibrium - max_mortality
) / pop_growth_equilibrium_sol
birthrate_pretransition_slope = (
    birthrate_at_transition - rate_at_equilibrium
) / pop_growth_transition_sol

birthrate_at_growth_max = (pop_growth_max_sol - pop_growth_transition_sol) * (
    (min_birthrate - birthrate_at_transition)
    / (pop_growth_stable_sol - pop_growth_transition_sol)
) + birthrate_at_transition
mortality_at_growth_max = birthrate_at_growth_max * max_growth_mortality_mult
mortality_equilibrium_to_growth_max_slope = (
    mortality_at_growth_max - rate_at_equilibrium
) / (pop_growth_max_sol - pop_growth_equilibrium_sol)
mortality_equilibrium_to_growth_max_intercept = (
    -mortality_equilibrium_to_growth_max_slope * pop_growth_equilibrium_sol
    + rate_at_equilibrium
)

birthrate_transition_slope = (min_birthrate - birthrate_at_transition) / (
    pop_growth_stable_sol - pop_growth_transition_sol
)
birthrate_transition_intercept = (
    -birthrate_transition_slope * pop_growth_stable_sol + min_birthrate
)

mortality_growth_max_to_stable_slope = (min_mortality - mortality_at_growth_max) / (
    pop_growth_stable_sol - pop_growth_max_sol
)
mortality_growth_max_to_stable_intercept = (
    -mortality_growth_max_to_stable_slope * pop_growth_stable_sol + min_mortality
)


# Define functions to calculate birthrate and mortality
def calculate_mortality(sol):
    if sol < pop_growth_equilibrium_sol:
        return sol * mortality_starving_slope + max_mortality
    elif sol < pop_growth_max_sol:
        return (
            sol * mortality_equilibrium_to_growth_max_slope
            + mortality_equilibrium_to_growth_max_intercept
        )
    elif sol < pop_growth_stable_sol:
        return (
            sol * mortality_growth_max_to_stable_slope
            + mortality_growth_max_to_stable_intercept
        )
    else:
        return min_mortality


def calculate_birthrate(sol):
    if sol < pop_growth_equilibrium_sol:
        return (sol * birthrate_pretransition_slope + max_birthrate) * (
            1 - 0.1 * (pop_growth_equilibrium_sol - sol)
        )
    elif sol < pop_growth_transition_sol:
        return sol * birthrate_pretransition_slope + max_birthrate
    elif sol < pop_growth_stable_sol:
        return sol * birthrate_transition_slope + birthrate_transition_intercept
    else:
        return min_birthrate


def population_distribution(sol, peak_sol, peak_width):
    norm = 1 / (peak_width * np.sqrt(2 * np.pi))
    return np.exp(-((sol - peak_sol) ** 2) / (2 * peak_width**2)) * norm


# convolve with population distribution
def calculate_mean_mortality(peak_sol, peak_width):
    return np.sum(
        [
            population_distribution(sol, peak_sol, peak_width)
            * calculate_mortality(sol)
            for sol in range(1, 100)
        ]
    )


def calculate_mean_birthrate(peak_sol, peak_width):
    return np.sum(
        [
            population_distribution(sol, peak_sol, peak_width)
            * calculate_birthrate(sol)
            for sol in range(1, 100)
        ]
    )


# Standard of Living (SoL) range
sol_range = np.linspace(1, 40, 400)
width = 5
birth_mult = 1
mortality_mult = 1

# Calculate birthrate, mortality, and overall growth rate
birthrates = np.array([birth_mult * calculate_birthrate(sol) for sol in sol_range])
mortalities = np.array([mortality_mult * calculate_mortality(sol) for sol in sol_range])
growth_rates = birthrates - mortalities

# Calculate mean birthrate, mortality, and overall growth rate
mean_birthrates = np.array(
    [birth_mult * calculate_mean_birthrate(sol, width) for sol in sol_range]
)
mean_mortalities = np.array(
    [mortality_mult * calculate_mean_mortality(sol, width) for sol in sol_range]
)
mean_growth_rates = mean_birthrates - mean_mortalities

# Plotting
plt.figure(figsize=(12, 8))
plt.plot(sol_range, birthrates, label="Birthrate", color="blue")
plt.plot(sol_range, mortalities, label="Mortality", color="red")
plt.plot(sol_range, growth_rates, label="Overall Growth Rate", color="green")
plt.plot(
    sol_range, mean_birthrates, label="Mean Birthrate", color="blue", linestyle="--"
)
plt.plot(
    sol_range, mean_mortalities, label="Mean Mortality", color="red", linestyle="--"
)
plt.plot(
    sol_range,
    mean_growth_rates,
    label="Mean Overall Growth Rate",
    color="green",
    linestyle="--",
)

plt.title(
    "Birthrate, Mortality, and Growth Rate as a function of Standard of Living (SoL)"
)
plt.xlabel("Standard of Living (SoL)")
plt.ylabel("Rate per Year")
plt.legend()
plt.grid(True)
plt.show()
