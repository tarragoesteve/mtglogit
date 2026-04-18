const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("svg")
  .attr("width", width)
  .attr("height", height);

// -----------------------------
// CONTAINER + ZOOM
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
    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(d => 200 + (1 - d.weight_norm) * 300)
      .strength(0.8)
    )
    .force("charge", d3.forceManyBody().strength(-1800))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("x", d3.forceX(width / 2).strength(0.08))
    .force("y", d3.forceY(width / 2).strength(0.08))
    .force("collide", d3.forceCollide()
      .radius(d => 35 + Math.pow(d.self_prob_norm, 1.5) * 90)
      .strength(0.6)
    );

  // -----------------------------
  // LINKS (weight)
  // -----------------------------
  const link = container.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", d => d3.interpolateRdYlGn(d.weight_norm))
    .attr("stroke-opacity", d => 0.25 + d.weight_norm * 0.75)
    .attr("stroke-width", d => 1 + Math.pow(d.weight_norm, 2.5) * 12)
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
  // COLOR = prob (GLOBAL QUALITY)
  // -----------------------------
  node.append("circle")
    .attr("r", d => 20 + Math.pow(d.self_prob_norm, 2.2) * 120)

    .attr("fill", d => {
      const p = d.prob_norm;

      return d3.interpolateRgbBasis([
        "#ff3b3b",  // bad
        "#ffcc33",  // mid
        "#2bff88"   // good
      ])(p);
    })

    .attr("stroke", d => {
      const p = d.prob_norm;

      return d3.interpolateRgbBasis([
        "#aa0000",
        "#cc8800",
        "#00cc66"
      ])(p);
    })

    .attr("stroke-width", 2);

  // -----------------------------
  // CLIP PATH (correct)
  // -----------------------------
  const defs = svg.append("defs");

  const clip = defs.selectAll("clipPath")
    .data(nodes)
    .join("clipPath")
    .attr("id", d => `clip-${d.id.replace(/[^a-zA-Z0-9]/g, "-")}`);

  clip.append("circle")
    .attr("cx", 0)
    .attr("cy", 0)
    .attr("r", d => 20 + Math.pow(d.self_prob_norm, 2.2) * 120);

  // -----------------------------
  // IMAGE
  // -----------------------------
  node.append("image")
    .attr("href", d => d.image)
    .attr("x", d => -(20 + Math.pow(d.self_prob_norm, 2.2) * 120))
    .attr("y", d => -(20 + Math.pow(d.self_prob_norm, 2.2) * 120))
    .attr("width", d => (20 + Math.pow(d.self_prob_norm, 2.2) * 120) * 2)
    .attr("height", d => (20 + Math.pow(d.self_prob_norm, 2.2) * 120) * 2)
    .attr("clip-path", d =>
      `url(#clip-${d.id.replace(/[^a-zA-Z0-9]/g, "-")})`
    );

  // -----------------------------
  // TOOLTIP
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

    node.attr("transform", d => `translate(${d.x}, ${d.y})`);
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