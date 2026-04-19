const CONFIG = {
  // -----------------------------
  // THRESHOLDS
  // -----------------------------
  LINK_VISIBLE_THRESHOLD: 1.1,
  LINK_HOVER_THRESHOLD: 1.02,

  // -----------------------------
  // SELF_PROB THRESHOLDS
  // -----------------------------
  SELF_PROB_HIGH: 1.05,
  SELF_PROB_LOW: 0.95,

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

// =============================
// DATASET CONFIGURATION
// =============================
const DEFAULT_DATASET = "Cube_Powered_Premier";

// Current dataset being displayed
let currentDataset = `data/${DEFAULT_DATASET}/data.json`;
let currentGraph = null;
let width, height, svg, container;
let availableDatasets = [];

// Get default dataset from URL parameter
function getDefaultDataset() {
  const params = new URLSearchParams(window.location.search);
  const paramDataset = params.get('dataset');
  
  if (paramDataset) {
    return paramDataset;
  }
  
  return `data/${DEFAULT_DATASET}/data.json`;
}

// Auto-detect all available datasets from datasets.json
async function autoDetectDatasets() {
  const baseFolder = "data/";
  availableDatasets = [];
  
  try {
    // Cargar datasets.json que contiene la lista de carpetas disponibles
    const response = await fetch('datasets.json');
    if (!response.ok) {
      throw new Error('datasets.json no encontrado');
    }
    
    const data = await response.json();
    
    // Validar que cada dataset tiene data.json
    for (const folder of data.datasets) {
      if (await checkDatasetExists(`${baseFolder}${folder}/data.json`)) {
        availableDatasets.push(folder);
      }
    }
    
    if (availableDatasets.length === 0) {
      console.warn('⚠️ No se encontraron datasets válidos en datasets.json');
    }
  } catch (error) {
    console.error('❌ Error cargando datasets.json:', error);
    console.log('Genere datasets.json ejecutando: python3 generate_datasets.py');
  }
  
  return availableDatasets;
}

// =============================
// CONFIG PANEL SETUP
// =============================
document.addEventListener("DOMContentLoaded", async () => {

  // Initialize SVG
  width = window.innerWidth;
  height = window.innerHeight;

  svg = d3.select("svg")
    .attr("width", width)
    .attr("height", height);

  // Zoom setup
  container = svg.append("g");

  svg.call(
    d3.zoom()
      .scaleExtent([0.2, 5])
      .on("zoom", (event) => {
        container.attr("transform", event.transform);
      })
  );

  const configBtn = document.getElementById("configBtn");
  const closeConfigBtn = document.getElementById("closeConfigBtn");
  const configPanel = document.getElementById("configPanel");
  const configOverlay = document.getElementById("configOverlay");
  const applyConfigBtn = document.getElementById("applyConfigBtn");
  const thresholdSlider = document.getElementById("thresholdSlider");
  const thresholdValue = document.getElementById("thresholdValue");
  const selfProbHighSlider = document.getElementById("selfProbHighSlider");
  const selfProbHighValue = document.getElementById("selfProbHighValue");
  const selfProbLowSlider = document.getElementById("selfProbLowSlider");
  const selfProbLowValue = document.getElementById("selfProbLowValue");
  const datasetSelect = document.getElementById("datasetSelect");

  // Set default dataset from URL parameter
  currentDataset = getDefaultDataset();

  // Load available datasets (WAIT for this to complete)
  await loadAvailableDatasets();

  // Load initial graph
  loadAndInitGraph(currentDataset);

  // Toggle config panel
  configBtn.addEventListener("click", () => {
    const isOpen = configPanel.style.display === "block";
    if (isOpen) {
      configPanel.style.display = "none";
      configOverlay.style.display = "none";
    } else {
      configPanel.style.display = "block";
      configOverlay.style.display = "block";
    }
  });

  closeConfigBtn.addEventListener("click", () => {
    configPanel.style.display = "none";
    configOverlay.style.display = "none";
  });

  configOverlay.addEventListener("click", () => {
    configPanel.style.display = "none";
    configOverlay.style.display = "none";
  });

  // Update threshold value display
  thresholdSlider.addEventListener("input", (e) => {
    thresholdValue.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Update SELF_PROB HIGH value display
  selfProbHighSlider.addEventListener("input", (e) => {
    selfProbHighValue.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Update SELF_PROB LOW value display
  selfProbLowSlider.addEventListener("input", (e) => {
    selfProbLowValue.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Apply configuration
  applyConfigBtn.addEventListener("click", () => {
    const newDataset = datasetSelect.value;
    const newThreshold = parseFloat(thresholdSlider.value);
    const newSelfProbHigh = parseFloat(selfProbHighSlider.value);
    const newSelfProbLow = parseFloat(selfProbLowSlider.value);

    // Update config
    CONFIG.LINK_VISIBLE_THRESHOLD = newThreshold;
    CONFIG.SELF_PROB_HIGH = newSelfProbHigh;
    CONFIG.SELF_PROB_LOW = newSelfProbLow;
    currentDataset = newDataset;

    // Reload graph
    loadAndInitGraph(newDataset);

    // Close panel
    configPanel.style.display = "none";
    configOverlay.style.display = "none";
  });
});

// Load available datasets from data/ folder
async function loadAvailableDatasets() {
  const datasetSelect = document.getElementById("datasetSelect");

  try {
    // Auto-detect all available datasets
    await autoDetectDatasets();
    
    // Clear existing options and add new ones
    datasetSelect.innerHTML = '';
    
    if (availableDatasets.length === 0) {
      const option = document.createElement("option");
      option.textContent = "No datasets found";
      option.disabled = true;
      datasetSelect.appendChild(option);
      return;
    }
    
    for (const folder of availableDatasets) {
      const option = document.createElement("option");
      option.value = `data/${folder}/data.json`;
      option.textContent = folder.charAt(0).toUpperCase() + folder.slice(1);
      datasetSelect.appendChild(option);
    }
    
    // Set the default value
    datasetSelect.value = getDefaultDataset();
  } catch (error) {
    console.error("Error loading datasets:", error);
  }
}

// Check if a dataset file exists
async function checkDatasetExists(path) {
  try {
    const response = await fetch(path, { method: "HEAD" });
    return response.ok;
  } catch {
    return false;
  }
}

// Load and initialize graph with specified dataset
async function loadAndInitGraph(datasetPath) {
  try {
    const response = await fetch(datasetPath);
    if (!response.ok) {
      throw new Error(`Dataset not found: ${datasetPath}`);
    }
    const data = await response.json();
    initGraph(data.nodes, data.links);
  } catch (error) {
    console.error("Error loading dataset:", error);
    alert(`Error loading dataset: ${error.message}`);
  }
}

// -----------------------------
// GRAPH
// -----------------------------
function initGraph(nodes, links) {

  // Clear previous graph
  container.selectAll("*").remove();

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
    .text(d =>
      d.weight >= CONFIG.LINK_HOVER_THRESHOLD ? d.weight.toFixed(2) : ""
    )
    .attr("fill", "#fff")
    .attr("font-size", d =>
      CONFIG.LABEL_FONT_BASE + d.weight_norm * CONFIG.LABEL_FONT_SCALE
    )
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

      if (s > CONFIG.SELF_PROB_HIGH) return "drop-shadow(0 0 10px #2bff88)";
      if (s < CONFIG.SELF_PROB_LOW) return "drop-shadow(0 0 10px #ff3b3b)";
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
        .attr("stroke-opacity", l => {
          const isConnected =
            l.source.id === d.id || l.target.id === d.id;

          if (isConnected && l.weight >= CONFIG.LINK_HOVER_THRESHOLD) return 1;
          if (!isConnected) return 0.05;

          return 0;
        })
        .attr("stroke-width", l => {
          const isConnected =
            l.source.id === d.id || l.target.id === d.id;

          if (isConnected && l.weight >= CONFIG.LINK_HOVER_THRESHOLD) {
            return CONFIG.LINK_WIDTH_HOVER_BASE + l.weight_norm * CONFIG.LINK_WIDTH_HOVER_SCALE;
          }

          if (l.weight < CONFIG.LINK_VISIBLE_THRESHOLD) return 0;

          return isConnected
            ? CONFIG.LINK_WIDTH_HOVER_BASE + l.weight_norm * CONFIG.LINK_WIDTH_HOVER_SCALE
            : CONFIG.LINK_WIDTH_BASE + Math.pow(l.weight_norm, 2.0) * CONFIG.LINK_WIDTH_SCALE;
        });

      // 🔥 SHOW LINK LABELS
      linkLabels
        .style("opacity", l => {
          const isConnected =
            l.source.id === d.id || l.target.id === d.id;

          return (isConnected && l.weight >= CONFIG.LINK_HOVER_THRESHOLD) ? 1 : 0;
        });

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

      link
        .attr("stroke-opacity", d =>
          d.weight >= CONFIG.LINK_VISIBLE_THRESHOLD ? 1 : 0
        )
        .attr("stroke-width", d =>
          d.weight < CONFIG.LINK_VISIBLE_THRESHOLD
            ? 0
            : CONFIG.LINK_WIDTH_BASE + Math.pow(d.weight_norm, 2.0) * CONFIG.LINK_WIDTH_SCALE
        );

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