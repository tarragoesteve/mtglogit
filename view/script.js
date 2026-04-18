const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("svg")
  .attr("width", width)
  .attr("height", height);

// -----------------------------
// CONTAINER (ZOOM)
// -----------------------------
const container = svg.append("g");

// -----------------------------
// ZOOM + PAN
// -----------------------------
const zoom = d3.zoom()
  .scaleExtent([0.2, 5])
  .on("zoom", (event) => {
    container.attr("transform", event.transform);
  });

svg.call(zoom);

// -----------------------------
// LOAD DATA
// -----------------------------
d3.json("data.json").then(data => {
  initGraph(data.nodes, data.links);
});

// -----------------------------
// GRAPH
// -----------------------------
function initGraph(nodes, links) {

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(160))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2));

  // -----------------------------
  // LINKS (RED -> GREEN)
  // -----------------------------
  const link = container.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", d => d3.interpolateRdYlGn(d.weight_norm))
    .attr("stroke-opacity", d => 0.2 + d.weight_norm * 0.8)
    .attr("stroke-width", d => 1 + Math.pow(d.weight_norm, 2) * 10);

  // -----------------------------
  // NODES
  // -----------------------------
  const node = container.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(drag(simulation));

  // -----------------------------
  // SELF SCORE NODE VISUAL
  // -----------------------------
  node.append("circle")
    .attr("r", d => 20 + Math.pow(d.prob_norm, 1.5) * 80)
    .attr("fill", d => d3.interpolateGreys(1 - d.self_prob_norm * 0.8))
    .attr("stroke", d => d3.interpolateGreens(d.self_prob_norm))
    .attr("stroke-width", d => 2 + d.self_prob_norm * 12)
    .style("filter", d => {

      if (d.self_prob_norm > 0.75) {
        return "drop-shadow(0 0 14px #00ff66)";
      }

      if (d.self_prob_norm > 0.5) {
        return "drop-shadow(0 0 6px #00aa44)";
      }

      return "none";
    });

  // -----------------------------
  // CLIP PATH (CIRCLE MASK)
  // -----------------------------
  node.append("clipPath")
    .attr("id", d => `clip-${d.id.replace(/[^a-zA-Z0-9]/g, "-")}`)
    .append("circle")
    .attr("r", d => 20 + Math.pow(d.prob_norm, 1.5) * 80);

  // -----------------------------
  // ART IMAGE (DEFAULT NODE IMAGE)
  // -----------------------------
  node.append("image")
    .attr("href", d => d.image)
    .attr("x", d => -(20 + Math.pow(d.prob_norm, 1.5) * 80))
    .attr("y", d => -(20 + Math.pow(d.prob_norm, 1.5) * 80))
    .attr("width", d => (20 + Math.pow(d.prob_norm, 1.5) * 80) * 2)
    .attr("height", d => (20 + Math.pow(d.prob_norm, 1.5) * 80) * 2)
    .attr("clip-path", d =>
      `url(#clip-${d.id.replace(/[^a-zA-Z0-9]/g, "-")})`
    )
    .style("opacity", d => 0.4 + d.self_prob_norm * 0.6);

  // -----------------------------
  // TOOLTIP (FULL CARD IMAGE)
  // -----------------------------
  node
    .on("mouseover", (event, d) => {
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

    node
      .attr("transform", d => `translate(${d.x}, ${d.y})`);
  });
}

// -----------------------------
// DRAG
// -----------------------------
function drag(simulation) {
  return d3.drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
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