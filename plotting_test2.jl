using CairoMakie
using JSON

data = JSON.parsefile("fault_scaling.json")

# Define the triplets we want to plot
target_triplets = [
    ("Server", "Network", "Scheduler"),
    ("EvilServer", "Network", "Scheduler"),
    ("RandomServer", "Network", "Scheduler"),
    ("SilentServer", "Network", "Scheduler"),
    # ("Server", "Network", "EvilFirstScheduler"),
    # ("EvilServer", "Network", "EvilFirstScheduler"),
    # ("RandomServer", "Network", "EvilFirstScheduler"),
    # ("SilentServer", "Network", "EvilFirstScheduler")
]

# Node counts
bad_counts = 1:7

series_data = Dict()

for triplet in target_triplets
    series_data[triplet] = Dict("bad nodes" => [], "rounds" => [])

    for n in eachindex(bad_counts)
        # Get results for this node count
        results = data[n]

        for result in results
            if (result["server"], result["network"], result["scheduler"]) == triplet
                push!(series_data[triplet]["bad nodes"], bad_counts[n])
                push!(series_data[triplet]["rounds"], result["rounds"])
                break
            end
        end
    end
end

# Create the plot
fig = Figure(resolution = (800, 600))
ax = Axis(fig[1, 1],
    xlabel = "Number of Bad Nodes",
    ylabel = "Rounds to Consensus",
    title = "Consensus Performance Comparison - Bad Nodes"
)

for (i, triplet) in enumerate(target_triplets)
    label = "$(triplet[1]) - $(triplet[2]) - $(triplet[3])"
    lines!(ax,
        series_data[triplet]["bad nodes"],
        series_data[triplet]["rounds"],
        label = label,
        linewidth = 2
    )
    scatter!(ax,
        series_data[triplet]["bad nodes"],
        series_data[triplet]["rounds"],
        markersize = 8
    )
end

axislegend(ax, position = :lt)

# Display the figure
fig

# save the figure
# save("consensus_plot.png", fig)
