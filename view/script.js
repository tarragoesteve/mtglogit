const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("svg")
  .attr("width", width)
  .attr("height", height);

// -----------------------------
// LOAD DATA
// -----------------------------
d3.json("data.json").then(data => {
  initGraph(data.nodes, data.links);
});

// -----------------------------
// MAIN GRAPH
// -----------------------------
function initGraph(nodes, links) {

  // -----------------------------
  // FORCE SIMULATION
  // -----------------------------
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(150))
    .force("charge", d3.forceManyBody().strength(-250))
    .force("center", d3.forceCenter(width / 2, height / 2));

  // -----------------------------
  // LINKS
  // -----------------------------
  const link = svg.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "#777")
    .attr("stroke-opacity", 0.6)
    .attr("stroke-width", d => 1 + d.weight_norm * 6);

  // -----------------------------
  // NODES
  // -----------------------------
  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(drag(simulation));

  // -----------------------------
  // NODE BASE (CIRCLE)
  // -----------------------------
  node.append("circle")
    .attr("r", d => 10 + d.prob_norm * 30)
    .attr("fill", "#222")
    .attr("stroke", d => d3.interpolateViridis(d.self_prob_norm))
    .attr("stroke-width", 3);

  // -----------------------------
  // NODE IMAGE
  // -----------------------------
  node.append("image")
    .attr("href", d => d.image)
    .attr("x", d => -(10 + d.prob_norm * 30))
    .attr("y", d => -(10 + d.prob_norm * 30))
    .attr("width", d => (10 + d.prob_norm * 30) * 2)
    .attr("height", d => (10 + d.prob_norm * 30) * 2)
    .attr("clip-path", "circle()");

  // -----------------------------
  // TICK UPDATE
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
// DRAG BEHAVIOR
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