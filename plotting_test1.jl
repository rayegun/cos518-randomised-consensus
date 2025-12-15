using CairoMakie
using JSON

# Read JSON file
data = JSON.parsefile("node_scaling_sqrt.json")

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
node_counts = [16, 21, 26, 50, 100]

series_data = Dict()

for triplet in target_triplets
    series_data[triplet] = Dict("nodes" => [], "messages" => [])

    for n in eachindex(node_counts)
        # Get results for this node count
        results = data[n]

        # Find the matching triplet
        for result in results
            if (result["server"], result["network"], result["scheduler"]) == triplet
                push!(series_data[triplet]["nodes"], node_counts[n])
                push!(series_data[triplet]["messages"], result["messages"])
                break
            end
        end
    end
end

# Create the plot
fig = Figure(resolution = (800, 600))
ax = Axis(fig[1, 1],
    xlabel = "Number of Nodes",
    ylabel = "Messages to Consensus",
    title = "Consensus Performance Comparison with constant fault rate √n"
)

for (i, triplet) in enumerate(target_triplets)
    label = "$(triplet[1]) - $(triplet[2]) - $(triplet[3])"
    lines!(ax,
        series_data[triplet]["nodes"],
        series_data[triplet]["messages"],
        label = label,
        linewidth = 2
    )
    scatter!(ax,
        series_data[triplet]["nodes"],
        series_data[triplet]["messages"],
        markersize = 8
    )
end

axislegend(ax, position = :lt)

# Display the figure
fig

# save the figure
# save("consensus_plot.png", fig)
