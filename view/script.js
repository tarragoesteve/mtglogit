const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("svg")
  .attr("width", width)
  .attr("height", height);

// -----------------------------
// ZOOM
// -----------------------------
const container = svg.append("g");

svg.call(
  d3.zoom()
    .scaleExtent([0.2, 5])
    .on("zoom", (event) => {
      container.attr("transform", event.transform);
    })
);

// -----------------------------
// DATA
// -----------------------------
d3.json("data.json").then(data => {
  initGraph(data.nodes, data.links);
});

// -----------------------------
// GRAPH
// -----------------------------
function initGraph(nodes, links) {

  const simulation = d3.forceSimulation(nodes)

    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(d => 190 + (1 - d.weight_norm) * 260)
      .strength(d => 0.5 + d.weight_norm * 0.9)
    )

    .force("charge", d3.forceManyBody().strength(-350))

    .force("center", d3.forceCenter(width / 2, height / 2).strength(0.9))

    .force("x", d3.forceX(width / 2).strength(0.04))
    .force("y", d3.forceY(height / 2).strength(0.04))

    .force("collide", d3.forceCollide()
      .radius(d => 26 + Math.pow(d.self_prob_norm, 1.2) * 95)
      .strength(0.7)
    );

  // -----------------------------
  // LINKS
  // -----------------------------
  const link = container.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", d => d3.interpolateRgbBasis([
      "#ffffff",
      "#F200FF",
    ])(d.weight_norm))
    .attr("stroke-width", d =>
      0.8 + Math.pow(d.weight_norm, 2.0) * 9
    )
    .attr("stroke-linecap", "round");

  // -----------------------------
  // NODES
  // -----------------------------
  const node = container.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(drag(simulation));

  // -----------------------------
  // SIZE
  // -----------------------------
  node.append("circle")
    .attr("r", d => 60 * d.prob)

    .attr("fill", d => d3.interpolateRgbBasis([
      "#ff3b3b",
      "#ffcc33",
      "#2bff88"
    ])(d.prob_norm))

    .attr("stroke", "#111")
    .attr("stroke-width", 2)

    // -----------------------------
    // ✨ SELF_PROB
    // -----------------------------
    .style("filter", d => {
      const s = d.self_prob_norm;

      if (s > 1.05) return "drop-shadow(0 0 10px #2bff88)";
      if (s < 0.95) return "drop-shadow(0 0 10px #ff3b3b)";
      return "drop-shadow(0 0 0px #000000)";
    });

  // -----------------------------
  // CLIP PATH
  // -----------------------------
  const defs = svg.append("defs");

  const clip = defs.selectAll("clipPath")
    .data(nodes)
    .join("clipPath")
    .attr("id", d => `clip-${d.id.replace(/[^a-zA-Z0-9]/g, "-")}`);

  clip.append("circle")
    .attr("r", d => 60 * d.prob)
    .attr("cx", 0)
    .attr("cy", 0);

  // -----------------------------
  // IMAGE
  // -----------------------------
  node.append("image")
    .attr("href", d => d.image)
    .attr("x", d => -(60 * d.prob))
    .attr("y", d => -(60 * d.prob))
    .attr("width", d => (60 * d.prob) * 2)
    .attr("height", d => (60 * d.prob) * 2)
    .attr("clip-path", d =>
      `url(#clip-${d.id.replace(/[^a-zA-Z0-9]/g, "-")})`
    );

  // -----------------------------
  // HOVER
  // -----------------------------
  node
    .on("mouseover", (event, d) => {

      const connected = new Set();

      links.forEach(l => {
        if (l.source.id === d.id) connected.add(l.target.id);
        if (l.target.id === d.id) connected.add(l.source.id);
      });

      link
        .attr("stroke-opacity", l =>
          l.source.id === d.id || l.target.id === d.id ? 1 : 0.05
        )
        .attr("stroke-width", l =>
          l.source.id === d.id || l.target.id === d.id
            ? 3 + l.weight_norm * 8
            : 0.8 + Math.pow(l.weight_norm, 2.0) * 9
        );

      node.style("opacity", n =>
        n.id === d.id || connected.has(n.id) ? 1 : 0.3
      );

      d3.select("#tooltip")
        .style("display", "block")
        .html(`<img src="${d.card_image}" />`);
    })

    .on("mousemove", (event) => {
      d3.select("#tooltip")
        .style("left", (event.pageX + 15) + "px")
        .style("top", (event.pageY + 15) + "px");
    })

    .on("mouseout", () => {

      link
        .attr("stroke-opacity", d => 1)
        .attr("stroke-width", d =>
          0.8 + Math.pow(d.weight_norm, 2.0) * 9
        );

      node.style("opacity", 1);

      d3.select("#tooltip").style("display", "none");
    });

  // -----------------------------
  // TICK
  // -----------------------------
  simulation.on("tick", () => {

    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node.attr("transform", d => `translate(${d.x}, ${d.y})`);
  });
}

// -----------------------------
// DRAG
// -----------------------------
function drag(simulation) {
  return d3.drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.25).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}