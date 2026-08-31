const sites = [
  {
    name: "IREN Sweetwater Campus",
    operator: "IREN",
    location: "Sweetwater, Texas, USA",
    lat: 32.47,
    lon: -100.41,
    capacity: "2.0 GW planned",
    stage: "Under construction",
    status: "high",
    signal: "Track grading, shells, switchyard, transformer yards, cooling gear, and ERCOT/AEP Texas grid evidence."
  },
  {
    name: "CoreWeave Lancaster",
    operator: "CoreWeave / data-center partners",
    location: "Lancaster, Pennsylvania, USA",
    lat: 40.04,
    lon: -76.31,
    capacity: "Representative AI campus",
    stage: "Expansion watch",
    status: "watch",
    signal: "Compare public capacity claims against visible substation and shell progress."
  },
  {
    name: "xAI Memphis Supercluster",
    operator: "xAI",
    location: "Memphis, Tennessee, USA",
    lat: 35.13,
    lon: -90.05,
    capacity: "Large GPU cluster",
    stage: "Operational expansion",
    status: "high",
    signal: "Watch power-generation, utility, cooling, and material-staging signals around accelerated buildout."
  },
  {
    name: "Northern Virginia Data Alley",
    operator: "Hyperscale / colocation cluster",
    location: "Ashburn, Virginia, USA",
    lat: 39.04,
    lon: -77.49,
    capacity: "Multi-campus region",
    stage: "Dense baseline",
    status: "stable",
    signal: "Use as a mature-market benchmark for energized shells, substations, and repeated expansion pads."
  },
  {
    name: "Lulea AI/HPC Region",
    operator: "European hyperscale operators",
    location: "Lulea, Sweden",
    lat: 65.58,
    lon: 22.15,
    capacity: "Nordic power/cooling hub",
    stage: "Cold-climate watch",
    status: "watch",
    signal: "Weather and seasonality matter; discount snow cover and low sun-angle imagery."
  },
  {
    name: "Dublin Data-Center Ring",
    operator: "Hyperscale / colocation cluster",
    location: "Dublin, Ireland",
    lat: 53.35,
    lon: -6.26,
    capacity: "Grid-constrained region",
    stage: "Permitting and grid watch",
    status: "watch",
    signal: "Correlate visible campus progress with grid-connection and permitting milestones."
  },
  {
    name: "Johor AI Infrastructure Corridor",
    operator: "Regional AI/cloud operators",
    location: "Johor, Malaysia",
    lat: 1.49,
    lon: 103.76,
    capacity: "Fast-growth regional hub",
    stage: "Rapid expansion",
    status: "high",
    signal: "Look for campus grading, new substations, and roadwork around announced AI capacity."
  },
  {
    name: "Tokyo Bay Compute Cluster",
    operator: "Japan cloud / colocation operators",
    location: "Tokyo, Japan",
    lat: 35.68,
    lon: 139.76,
    capacity: "Metro cluster",
    stage: "Baseline watch",
    status: "stable",
    signal: "Monitor dense urban expansion where imagery needs non-imagery confirmation."
  }
];

const canvas = document.querySelector("#globe");
const ctx = canvas.getContext("2d");
const siteList = document.querySelector("#site-list");
const toggle = document.querySelector("#rotation-toggle");
const siteName = document.querySelector("#site-name");
const siteLocation = document.querySelector("#site-location");
const siteOperator = document.querySelector("#site-operator");
const siteStage = document.querySelector("#site-stage");
const siteSignal = document.querySelector("#site-signal");

const colors = {
  high: "#ff6b6b",
  watch: "#f4c95d",
  stable: "#76db8b"
};

let rotation = -1.55;
let tilt = -0.28;
let selectedIndex = 0;
let paused = false;
let dragging = false;
let lastPointer = null;
let lastFrame = performance.now();
const captureFrame = new URLSearchParams(window.location.search).get("captureFrame");

if (captureFrame !== null) {
  paused = true;
  rotation = -1.55 + Number(captureFrame) * 0.07;
}

function resizeCanvas() {
  const size = Math.floor(canvas.getBoundingClientRect().width);
  const ratio = window.devicePixelRatio || 1;
  canvas.width = size * ratio;
  canvas.height = size * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function project(lat, lon, radius, center) {
  const phi = (lat * Math.PI) / 180;
  const lambda = (lon * Math.PI) / 180 + rotation;
  const cosPhi = Math.cos(phi);
  const x = radius * cosPhi * Math.sin(lambda);
  const y = radius * (Math.sin(phi) * Math.cos(tilt) - cosPhi * Math.cos(lambda) * Math.sin(tilt));
  const z = cosPhi * Math.cos(lambda) * Math.cos(tilt) + Math.sin(phi) * Math.sin(tilt);

  return {
    x: center.x + x,
    y: center.y - y,
    visible: z > -0.06,
    depth: z
  };
}

function drawCircle(center, radius) {
  const gradient = ctx.createRadialGradient(center.x - radius * 0.3, center.y - radius * 0.35, radius * 0.1, center.x, center.y, radius);
  gradient.addColorStop(0, "#1d5a69");
  gradient.addColorStop(0.58, "#12394a");
  gradient.addColorStop(1, "#07151d");

  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();
  ctx.strokeStyle = "rgba(117, 231, 220, 0.42)";
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

function drawGraticule(center, radius) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
  ctx.clip();
  ctx.strokeStyle = "rgba(191, 230, 225, 0.14)";
  ctx.lineWidth = 1;

  for (let lat = -60; lat <= 60; lat += 30) {
    drawPath(Array.from({ length: 145 }, (_, i) => ({ lat, lon: -180 + i * 2.5 })), center, radius);
  }

  for (let lon = -180; lon < 180; lon += 30) {
    drawPath(Array.from({ length: 97 }, (_, i) => ({ lat: -80 + i * 1.6667, lon })), center, radius);
  }

  ctx.restore();
}

function drawLand(center, radius) {
  const landMasses = [
    [[72, -168], [58, -132], [50, -95], [27, -82], [17, -99], [25, -124], [49, -126], [62, -150]],
    [[13, -82], [-18, -78], [-54, -67], [-34, -52], [-10, -45], [8, -61]],
    [[70, -10], [58, 30], [35, 42], [12, 20], [6, -12], [36, -10]],
    [[35, 42], [58, 78], [52, 132], [20, 122], [6, 78], [12, 45]],
    [[31, -18], [5, 18], [-34, 22], [-35, 48], [4, 42], [20, 30]],
    [[8, 95], [-10, 118], [-38, 145], [-24, 155], [5, 132]],
    [[-12, 112], [-44, 114], [-39, 153], [-18, 151]]
  ];

  ctx.save();
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
  ctx.clip();
  ctx.fillStyle = "rgba(61, 118, 84, 0.72)";
  ctx.strokeStyle = "rgba(134, 190, 151, 0.28)";
  ctx.lineWidth = 1;

  landMasses.forEach((points) => {
    const projected = points.map(([lat, lon]) => project(lat, lon, radius, center));
    ctx.beginPath();
    projected.forEach((point, index) => {
      if (index === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  });

  ctx.restore();
}

function drawPath(points, center, radius) {
  ctx.beginPath();
  let started = false;
  points.forEach(({ lat, lon }) => {
    const point = project(lat, lon, radius, center);
    if (!point.visible) {
      started = false;
      return;
    }
    if (!started) {
      ctx.moveTo(point.x, point.y);
      started = true;
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();
}

function drawMarkers(center, radius, elapsed) {
  const sorted = sites
    .map((site, index) => ({ site, index, point: project(site.lat, site.lon, radius, center) }))
    .sort((a, b) => a.point.depth - b.point.depth);

  sorted.forEach(({ site, index, point }) => {
    if (!point.visible) return;

    const active = index === selectedIndex;
    const markerRadius = active ? 8 : 5.5;
    const pulse = active ? 9 + Math.sin(elapsed / 220) * 3 : 0;

    if (active) {
      ctx.beginPath();
      ctx.arc(point.x, point.y, pulse + markerRadius, 0, Math.PI * 2);
      ctx.fillStyle = `${colors[site.status]}22`;
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(point.x, point.y, markerRadius, 0, Math.PI * 2);
    ctx.fillStyle = colors[site.status];
    ctx.shadowColor = colors[site.status];
    ctx.shadowBlur = active ? 18 : 10;
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.beginPath();
    ctx.arc(point.x, point.y, markerRadius + 2.5, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.85)";
    ctx.lineWidth = active ? 2 : 1;
    ctx.stroke();
  });
}

function draw() {
  const now = performance.now();
  const delta = now - lastFrame;
  lastFrame = now;
  if (!paused && !dragging) rotation += delta * 0.000045;

  const width = canvas.getBoundingClientRect().width;
  const center = { x: width / 2, y: width / 2 };
  const radius = width * 0.43;

  ctx.clearRect(0, 0, width, width);
  drawCircle(center, radius);
  drawLand(center, radius);
  drawGraticule(center, radius);
  drawMarkers(center, radius, now);
  requestAnimationFrame(draw);
}

function updateSelected(index) {
  selectedIndex = index;
  const site = sites[index];
  siteName.textContent = site.name;
  siteLocation.textContent = site.location;
  siteOperator.textContent = site.operator;
  siteStage.textContent = `${site.stage} | ${site.capacity}`;
  siteSignal.textContent = site.signal;

  document.querySelectorAll(".site-card").forEach((card, cardIndex) => {
    card.classList.toggle("active", cardIndex === index);
  });
}

function renderList() {
  document.querySelector("#site-count").textContent = sites.length;
  document.querySelector("#capacity-count").textContent = "4+ GW";
  document.querySelector("#alert-count").textContent = sites.filter((site) => site.status === "high").length;

  siteList.innerHTML = "";
  sites.forEach((site, index) => {
    const button = document.createElement("button");
    button.className = "site-card";
    button.type = "button";
    button.innerHTML = `<strong><i class="status ${site.status}"></i>${site.name}</strong><span>${site.location} / ${site.stage}</span>`;
    button.addEventListener("click", () => {
      const projectedLon = (-site.lon * Math.PI) / 180;
      rotation = projectedLon;
      updateSelected(index);
    });
    siteList.appendChild(button);
  });
}

function nearestSite(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  const center = { x: rect.width / 2, y: rect.height / 2 };
  const radius = rect.width * 0.43;
  const x = clientX - rect.left;
  const y = clientY - rect.top;

  return sites.reduce((best, site, index) => {
    const point = project(site.lat, site.lon, radius, center);
    if (!point.visible) return best;
    const distance = Math.hypot(point.x - x, point.y - y);
    return distance < best.distance ? { index, distance } : best;
  }, { index: -1, distance: 24 });
}

canvas.addEventListener("pointerdown", (event) => {
  dragging = true;
  lastPointer = { x: event.clientX, y: event.clientY };
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  if (!dragging || !lastPointer) return;
  rotation += (event.clientX - lastPointer.x) * 0.006;
  tilt = Math.max(-0.8, Math.min(0.8, tilt + (event.clientY - lastPointer.y) * 0.004));
  lastPointer = { x: event.clientX, y: event.clientY };
});

canvas.addEventListener("pointerup", (event) => {
  dragging = false;
  lastPointer = null;
  const nearest = nearestSite(event.clientX, event.clientY);
  if (nearest.index >= 0) updateSelected(nearest.index);
});

toggle.addEventListener("click", () => {
  paused = !paused;
  toggle.textContent = paused ? "Rotate" : "Pause";
});

window.addEventListener("resize", resizeCanvas);

renderList();
resizeCanvas();
updateSelected(0);
requestAnimationFrame(draw);
