const CONFIG = {
  // -----------------------------
  // THRESHOLDS
  // -----------------------------
  LINK_VISIBLE_THRESHOLD: 1.1,
  LINK_HOVER_THRESHOLD: 1.02,

  // -----------------------------
  // NODE SIZE
  // -----------------------------
  NODE_SIZE_MULT: 60,

  // -----------------------------
  // LINK STYLE
  // -----------------------------
  LINK_WIDTH_BASE: 0.8,
  LINK_WIDTH_SCALE: 9,
  LINK_WIDTH_HOVER_BASE: 3,
  LINK_WIDTH_HOVER_SCALE: 8,

  // -----------------------------
  // LINK LABELS
  // -----------------------------
  LABEL_FONT_BASE: 15,
  LABEL_FONT_SCALE: 20,

  // -----------------------------
  // FORCES
  // -----------------------------
  CHARGE_STRENGTH: -1450,
  CENTER_STRENGTH: 0.95,
  GRAVITY_STRENGTH: 0.07,

  // -----------------------------
  // COLLISION
  // -----------------------------
  COLLISION_BASE: 26,
  COLLISION_SCALE: 95,

  // -----------------------------
  // LINK FORCE
  // -----------------------------
  LINK_DISTANCE_BASE: 190,
  LINK_DISTANCE_SCALE: 260,
  LINK_STRENGTH_BASE: 0.5,
  LINK_STRENGTH_SCALE: 0.9,
};

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

    // -----------------------------
    // LINKS
    // -----------------------------
    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(d =>
        CONFIG.LINK_DISTANCE_BASE + (1 - d.weight_norm) * CONFIG.LINK_DISTANCE_SCALE
      )
      .strength(d =>
        CONFIG.LINK_STRENGTH_BASE + d.weight_norm * CONFIG.LINK_STRENGTH_SCALE
      )
    )

    // -----------------------------
    // 🔼 MORE SEPARATION
    // -----------------------------
    .force("charge", d3.forceManyBody().strength(CONFIG.CHARGE_STRENGTH))

    // -----------------------------
    // CENTER STABILITY
    // -----------------------------
    .force("center", d3.forceCenter(width / 2, height / 2).strength(CONFIG.CENTER_STRENGTH))

    // -----------------------------
    // SOFT GRAVITY
    // -----------------------------
    .force("x", d3.forceX(width / 2).strength(CONFIG.GRAVITY_STRENGTH))
    .force("y", d3.forceY(height / 2).strength(CONFIG.GRAVITY_STRENGTH))

    // -----------------------------
    // COLLISION (slightly looser)
    // -----------------------------
    .force("collide", d3.forceCollide()
      .radius(d =>
        CONFIG.COLLISION_BASE + Math.pow(d.self_prob_norm, 1.2) * CONFIG.COLLISION_SCALE
      )
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
      d.weight < CONFIG.LINK_VISIBLE_THRESHOLD
        ? 0
        : CONFIG.LINK_WIDTH_BASE + Math.pow(d.weight_norm, 2.0) * CONFIG.LINK_WIDTH_SCALE
    )
    .attr("stroke-opacity", d =>
      d.weight >= CONFIG.LINK_VISIBLE_THRESHOLD ? 1 : 0
    )
    .attr("stroke-linecap", "round");

  // 🔥 LINK LABELS (weight)
  const linkLabels = container.append("g")
    .selectAll("text")
    .data(links)
    .join("text")
    .text(d => d.weight.toFixed(2))
    .attr("fill", "#fff")
    .attr("font-size", d => 10 + d.weight_norm * 18)
    .attr("stroke", "#000")
    .attr("stroke-width", 3)
    .attr("paint-order", "stroke")
    .attr("text-anchor", "middle")
    .style("pointer-events", "none")
    .style("opacity", 0);

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
    .attr("r", d => CONFIG.NODE_SIZE_MULT * d.prob)

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
      const s = d.self_prob;

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
    .attr("r", d => CONFIG.NODE_SIZE_MULT * d.prob)
    .attr("cx", 0)
    .attr("cy", 0);

  // -----------------------------
  // IMAGE
  // -----------------------------
  node.append("image")
    .attr("href", d => d.image)
    .attr("x", d => -(CONFIG.NODE_SIZE_MULT * d.prob))
    .attr("y", d => -(CONFIG.NODE_SIZE_MULT * d.prob))
    .attr("width", d => (CONFIG.NODE_SIZE_MULT * d.prob) * 2)
    .attr("height", d => (CONFIG.NODE_SIZE_MULT * d.prob) * 2)
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
        );

      // 🔥 SHOW LINK LABELS
      linkLabels
        .style("opacity", l =>
          l.source.id === d.id || l.target.id === d.id ? 1 : 0
        );

      node.style("opacity", n =>
        n.id === d.id || connected.has(n.id) ? 1 : 0.3
      );

      // 🔥 TOOLTIP CONTENT
      d3.select("#tooltip")
        .style("display", "block")
        .html(`
          <img src="${d.card_image}" />
          <div style="color:white; margin-top:6px; font-size:12px;">
            <b>${d.id}</b><br/>
            Odds win if draw: ${d.prob.toFixed(3)}<br/>
            Odds of self draw: ${d.self_prob ? d.self_prob.toFixed(3) : "N/A"}
          </div>
        `);
    })

    .on("mousemove", (event) => {

      const tooltip = d3.select("#tooltip");

      const tooltipNode = tooltip.node();
      const w = tooltipNode.offsetWidth;
      const h = tooltipNode.offsetHeight;

      let x = event.pageX + 15;
      let y = event.pageY + 15;

      // 🔥 KEEP INSIDE SCREEN
      if (x + w > window.innerWidth) {
        x = event.pageX - w - 15;
      }

      if (y + h > window.innerHeight) {
        y = event.pageY - h - 15;
      }

      tooltip
        .style("left", x + "px")
        .style("top", y + "px");
    })

    .on("mouseout", () => {

      link.attr("stroke-opacity", 1);

      linkLabels.style("opacity", 0);

      linkLabels.style("opacity", 0);

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

    // 🔥 POSITION LABELS
    linkLabels
      .attr("x", d => (d.source.x + d.target.x) / 2)
      .attr("y", d => (d.source.y + d.target.y) / 2);

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