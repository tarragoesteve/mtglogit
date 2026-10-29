const CONFIG = {
  // -----------------------------
  // THRESHOLDS
  // -----------------------------
  LINK_VISIBLE_THRESHOLD: 1.3,
  LINK_HOVER_THRESHOLD: 1.15,

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
  // MAX LINKS
  // -----------------------------
  MAX_LINKS: 500,

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
let datasetData = null;
let currentView = "graph";
let graphNeedsUpdate = true;
let loadRequest = 0;
let activeTab = "alone";
const tableState = Object.fromEntries(
  ["alone", "self", "pairs"].map(tab => [
    tab, { sortKey: "weight", direction: "descending", minimumGames: 0 }
  ])
);

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
  const hoverThresholdSlider = document.getElementById("hoverThresholdSlider");
  const hoverThresholdValue = document.getElementById("hoverThresholdValue");
  const selfProbHighSlider = document.getElementById("selfProbHighSlider");
  const selfProbHighValue = document.getElementById("selfProbHighValue");
  const selfProbLowSlider = document.getElementById("selfProbLowSlider");
  const selfProbLowValue = document.getElementById("selfProbLowValue");
  const maxLinksInput = document.getElementById("maxLinksInput");
  const maxLinksValue = document.getElementById("maxLinksValue");
  const datasetSelect = document.getElementById("datasetSelect");
  document.getElementById("tableViewToggle").addEventListener("change", (event) => {
    setView(event.target.checked ? "table" : "graph");
  });
  setupTableControls();

  // Initialize slider values from CONFIG (single source of truth)
  thresholdSlider.value = CONFIG.LINK_VISIBLE_THRESHOLD;
  thresholdValue.textContent = CONFIG.LINK_VISIBLE_THRESHOLD.toFixed(2);
  hoverThresholdSlider.value = CONFIG.LINK_HOVER_THRESHOLD;
  hoverThresholdValue.textContent = CONFIG.LINK_HOVER_THRESHOLD.toFixed(2);
  selfProbHighSlider.value = CONFIG.SELF_PROB_HIGH;
  selfProbHighValue.textContent = CONFIG.SELF_PROB_HIGH.toFixed(2);
  selfProbLowSlider.value = CONFIG.SELF_PROB_LOW;
  selfProbLowValue.textContent = CONFIG.SELF_PROB_LOW.toFixed(2);
  maxLinksInput.value = CONFIG.MAX_LINKS;
  maxLinksValue.textContent = CONFIG.MAX_LINKS;

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

  // Update LINK HOVER THRESHOLD value display
  hoverThresholdSlider.addEventListener("input", (e) => {
    hoverThresholdValue.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Update SELF_PROB HIGH value display
  selfProbHighSlider.addEventListener("input", (e) => {
    selfProbHighValue.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Update SELF_PROB LOW value display
  selfProbLowSlider.addEventListener("input", (e) => {
    selfProbLowValue.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Update MAX LINKS value display
  maxLinksInput.addEventListener("input", (e) => {
    maxLinksValue.textContent = parseInt(e.target.value);
  });

  // Apply configuration
  applyConfigBtn.addEventListener("click", () => {
    const newDataset = datasetSelect.value;
    const newThreshold = parseFloat(thresholdSlider.value);
    const newHoverThreshold = parseFloat(hoverThresholdSlider.value);
    const newSelfProbHigh = parseFloat(selfProbHighSlider.value);
    const newSelfProbLow = parseFloat(selfProbLowSlider.value);
    const newMaxLinks = parseInt(maxLinksInput.value);

    // Update config
    CONFIG.MAX_LINKS = newMaxLinks;
    CONFIG.LINK_VISIBLE_THRESHOLD = newThreshold;
    CONFIG.LINK_HOVER_THRESHOLD = newHoverThreshold;
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
  const request = ++loadRequest;
  const status = document.getElementById("dataStatus");
  status.textContent = "Loading dataset...";
  status.hidden = false;
  currentGraph?.stop();
  datasetData = null;
  renderTable();
  try {
    const response = await fetch(datasetPath);
    if (!response.ok) {
      throw new Error(`Dataset not found: ${datasetPath}`);
    }
    const data = await response.json();
    if (request !== loadRequest) return;
    datasetData = data;
    graphNeedsUpdate = true;
    status.hidden = true;
    setView(currentView);
  } catch (error) {
    if (request !== loadRequest) return;
    console.error("Error loading dataset:", error);
    currentGraph?.stop();
    datasetData = null;
    container.selectAll("*").remove();
    svg.selectAll("defs").remove();
    renderTable();
    status.textContent = `Error loading dataset: ${error.message}`;
    status.hidden = false;
  }
}

function setView(view) {
  currentView = view;
  const showTable = view === "table";
  svg.attr("hidden", showTable ? "" : null);
  document.getElementById("tableView").hidden = !showTable;
  document.getElementById("graphSettings").hidden = showTable;
  document.getElementById("tooltip").style.display = "none";
  if (showTable) {
    currentGraph?.stop();
    renderTable();
  } else if (datasetData) {
    if (graphNeedsUpdate) {
      // D3 mutates nodes and link endpoints; keep the loaded dataset untouched.
      const nodes = datasetData.nodes.map(node => ({ ...node }));
      const links = datasetData.links
        .map(link => ({ ...link }))
        .sort((a, b) => b.weight - a.weight)
        .slice(0, CONFIG.MAX_LINKS);
      initGraph(nodes, links);
      graphNeedsUpdate = false;
    } else {
      currentGraph?.restart();
    }
  }
}

function setupTableControls() {
  const body = document.querySelector("#weightsTable tbody");
  function showPreview(event) {
    const name = event.target.closest(".card-name");
    if (!name) return;
    const tooltip = document.getElementById("tooltip");
    const caption = document.createElement("div");
    caption.textContent = name.textContent;
    const bounds = name.getBoundingClientRect();
    const x = event.type === "focusin" ? bounds.left : event.clientX;
    const y = event.type === "focusin" ? bounds.bottom : event.clientY;
    tooltip.replaceChildren(caption);
    if (name.dataset.cardImage) {
      const image = document.createElement("img");
      image.alt = name.textContent;
      image.addEventListener("load", () => {
        if (tooltip.contains(image)) positionTooltip(x, y);
      });
      image.addEventListener("error", () => {
        if (!tooltip.contains(image)) return;
        image.remove();
        const message = document.createElement("div");
        message.textContent = "Card image unavailable.";
        tooltip.appendChild(message);
        positionTooltip(x, y);
      });
      image.src = name.dataset.cardImage;
      tooltip.prepend(image);
    } else {
      const message = document.createElement("div");
      message.textContent = "Card image unavailable.";
      tooltip.appendChild(message);
    }
    tooltip.style.display = "block";
    positionTooltip(x, y);
  }
  body.addEventListener("mouseover", showPreview);
  body.addEventListener("focusin", showPreview);
  body.addEventListener("mousemove", (event) => {
    if (event.target.closest(".card-name")) positionTooltip(event.clientX, event.clientY);
  });
  const hidePreview = () => {
    document.getElementById("tooltip").style.display = "none";
  };
  body.addEventListener("mouseout", hidePreview);
  body.addEventListener("focusout", hidePreview);
  document.getElementById("weightsPanel").addEventListener("scroll", hidePreview);
  body.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hidePreview();
  });
  const tabs = Array.from(document.querySelectorAll("[data-tab]"));
  function selectTab(tab) {
    activeTab = tab.dataset.tab;
    for (const button of tabs) {
      const selected = button === tab;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
    }
    document.getElementById("weightsPanel").setAttribute("aria-labelledby", tab.id);
    const input = document.getElementById("minimumGames");
    input.value = tableState[activeTab].minimumGames;
    input.removeAttribute("aria-invalid");
    document.getElementById("gamesError").textContent = "";
    renderTable();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectTab(tab));
    tab.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      tabs[next].focus();
      selectTab(tabs[next]);
    });
  });
  document.getElementById("minimumGames").addEventListener("input", (event) => {
    const input = event.target;
    const valid = input.checkValidity() && Number.isSafeInteger(input.valueAsNumber);
    input.setAttribute("aria-invalid", String(!valid));
    document.getElementById("gamesError").textContent = valid
      ? "" : "Enter a whole number of games, zero or greater.";
    if (!valid) return;
    tableState[activeTab].minimumGames = input.valueAsNumber;
    renderTable();
  });
}

function renderTable() {
  document.getElementById("tooltip").style.display = "none";
  const state = tableState[activeTab];
  const columns = activeTab === "pairs"
    ? [["source", "Card 1"], ["target", "Card 2"], ["weight", "Weight"], ["games", "Games"]]
    : [["card", "Card"], ["weight", "Weight"], ["games", "Games"]];
  const descriptions = {
    alone: "Games: card present in the modeled game data.",
    self: "Games: repeated card (2+ copies) present in the modeled game data.",
    pairs: "Games: both cards present in the modeled game data. Includes all modeled pairs."
  };
  document.getElementById("tableDescription").textContent =
    `${descriptions[activeTab]} Weight is an odds multiplier: 1 is neutral.`;

  const head = document.querySelector("#weightsTable thead");
  const focusedKey = head.contains(document.activeElement)
    ? document.activeElement.dataset.sortKey : null;
  const header = document.createElement("tr");
  for (const [key, label] of columns) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.setAttribute("aria-sort", state.sortKey === key ? state.direction : "none");
    if (key === "weight" || key === "games") cell.className = "numeric";
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.sortKey = key;
    const indicator = state.direction === "ascending" ? " ↑" : " ↓";
    button.textContent = label + (state.sortKey === key ? indicator : "");
    button.addEventListener("click", () => {
      state.direction = state.sortKey === key && state.direction === "descending"
        ? "ascending" : "descending";
      state.sortKey = key;
      renderTable();
    });
    cell.appendChild(button);
    header.appendChild(cell);
  }
  head.replaceChildren(header);
  if (focusedKey) head.querySelector(`[data-sort-key="${focusedKey}"]`).focus();

  const hasTableData = datasetData && datasetData.tables
    && ["alone", "self", "pairs"].every(tab => Array.isArray(datasetData.tables[tab]));
  const tableError = document.getElementById("tableError");
  tableError.hidden = !datasetData || Boolean(hasTableData);
  tableError.textContent = tableError.hidden
    ? "" : "Table data is missing. Regenerate this dataset with wrinfo.py.";
  const allRows = hasTableData ? datasetData.tables[activeTab] : [];
  const rows = allRows.filter(row => row.games >= state.minimumGames);
  const multiplier = state.direction === "ascending" ? 1 : -1;
  rows.sort((a, b) => {
    const left = a[state.sortKey];
    const right = b[state.sortKey];
    const comparison = typeof left === "number"
      ? left - right : left.localeCompare(right);
    return comparison * multiplier
      || (a.card || a.source).localeCompare(b.card || b.source)
      || (a.target || "").localeCompare(b.target || "");
  });
  const body = document.createDocumentFragment();
  const cardImages = new Map((datasetData?.nodes || []).map(node => [node.id, node.card_image]));
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const [key] of columns) {
      const cell = document.createElement("td");
      if (key === "weight" || key === "games") cell.className = "numeric";
      if (key === "weight" || key === "games") {
        cell.textContent = key === "weight" ? row[key].toFixed(3) : String(row[key]);
      } else {
        const name = document.createElement("span");
        name.className = "card-name";
        name.tabIndex = 0;
        name.textContent = row[key];
        name.dataset.cardImage = cardImages.get(row[key]) || "";
        cell.appendChild(name);
      }
      tr.appendChild(cell);
    }
    body.appendChild(tr);
  }
  if (hasTableData && rows.length === 0) {
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.textContent = "No rows match the minimum-games filter.";
    const tr = document.createElement("tr");
    tr.appendChild(cell);
    body.appendChild(tr);
  }
  document.querySelector("#weightsTable tbody").replaceChildren(body);
  document.getElementById("rowCount").textContent = hasTableData
    ? `${rows.length.toLocaleString()} of ${allRows.length.toLocaleString()} rows`
    : datasetData ? "Table data unavailable." : "No dataset loaded.";
}

function positionTooltip(x, y) {
  const tooltip = document.getElementById("tooltip");
  const { width, height } = tooltip.getBoundingClientRect();
  const left = x + width + 15 > window.innerWidth ? x - width - 15 : x + 15;
  const top = y + height + 15 > window.innerHeight ? y - height - 15 : y + 15;
  tooltip.style.left = `${Math.max(8, Math.min(left, window.innerWidth - width - 8))}px`;
  tooltip.style.top = `${Math.max(8, Math.min(top, window.innerHeight - height - 8))}px`;
}

// -----------------------------
// GRAPH
// -----------------------------
function initGraph(nodes, links) {

  // Clear previous graph
  currentGraph?.stop();
  container.selectAll("*").remove();
  svg.selectAll("defs").remove();

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

  currentGraph = simulation;

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
      "rgb(255, 0, 0)",
      "#ffff00",
      "#00ff00"
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
      positionTooltip(event.clientX, event.clientY);
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