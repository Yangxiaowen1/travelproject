const SESSION_KEY = "travel_project_current_user";
const SESSION_COOKIE = "travel_project_session";
const SESSION_PARAM = "session";

const palette = {
  green: "#65ff9c",
  cyan: "#59ffd7",
  amber: "#d5ff68",
  mint: "#92ffd0",
  line: "rgba(110,255,175,.12)",
  axis: "#9ec9b0",
};

const state = {
  currentUser: null,
  role: "tourist",
  frontend: null,
  flow: null,
  portrait: null,
  homeNews: [],
  homeNewsUpdatedAt: "",
  charts: {},
};

function $(id) {
  return document.getElementById(id);
}

function html(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

function fmt(value) {
  if (value === null || value === undefined || value === "") return "-";
  const num = Number(value);
  return Number.isNaN(num) ? String(value) : new Intl.NumberFormat("zh-CN").format(Math.round(num));
}

function dec(value, digits = 1) {
  const num = Number(value);
  return Number.isNaN(num) ? "-" : num.toFixed(digits);
}

function formatShortDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function formatNewsTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function readSessionCookie() {
  try {
    const cookie = String(document.cookie || "")
      .split("; ")
      .find((item) => item.startsWith(`${SESSION_COOKIE}=`));
    if (!cookie) return "";
    return decodeURIComponent(cookie.slice(SESSION_COOKIE.length + 1));
  } catch {
    return "";
  }
}

function readSessionQuery() {
  try {
    const value = new URLSearchParams(window.location.search).get(SESSION_PARAM) || "";
    return value ? decodeURIComponent(value) : "";
  } catch {
    return "";
  }
}

function persistSessionPayload(payload) {
  if (!payload) return;
  try {
    localStorage.setItem(SESSION_KEY, payload);
  } catch {}
  try {
    document.cookie = `${SESSION_COOKIE}=${encodeURIComponent(payload)}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
  } catch {}
}

function restoreSession() {
  try {
    let raw = "";
    try {
      raw = localStorage.getItem(SESSION_KEY) || "";
    } catch {}
    if (!raw) raw = readSessionCookie();
    if (!raw) raw = readSessionQuery();
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (!data?.user) return false;
    state.currentUser = data.user;
    state.role = data.role === "operator" ? "operator" : "tourist";
    persistSessionPayload(raw);
    try {
      const url = new URL(window.location.href);
      if (url.searchParams.has(SESSION_PARAM)) {
        url.searchParams.delete(SESSION_PARAM);
        window.history.replaceState({}, "", url.toString());
      }
    } catch {}
    return true;
  } catch {
    return false;
  }
}

function clearSession() {
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {}
  try {
    document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
  } catch {}
}

async function fetchJson(path) {
  const res = await fetch(path);
  const body = await res.json();
  if (!body.success) throw new Error(body.message || "请求失败");
  return body.data;
}

function baseChart() {
  return {
    backgroundColor: "transparent",
    textStyle: { color: "#eefff4", fontFamily: "Microsoft YaHei, PingFang SC, sans-serif" },
    animationDuration: 700,
  };
}

function setBar(id, names, values, colors = [palette.green, palette.cyan]) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 118, right: 18, top: 26, bottom: 20 },
    xAxis: {
      type: "value",
      axisLabel: { color: palette.axis },
      splitLine: { lineStyle: { color: palette.line } },
    },
    yAxis: {
      type: "category",
      data: names,
      axisLabel: { color: "#defde9", width: 94, overflow: "truncate" },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    series: [{
      type: "bar",
      data: values,
      barMaxWidth: 18,
      itemStyle: {
        borderRadius: [0, 10, 10, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: colors[0] },
          { offset: 1, color: colors[1] },
        ]),
      },
    }],
  });
}

function setLine(id, names, values, color = palette.cyan) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    tooltip: { trigger: "axis" },
    grid: { left: 44, right: 18, top: 28, bottom: 24 },
    xAxis: {
      type: "category",
      data: names,
      axisLabel: { color: palette.axis },
      axisLine: { lineStyle: { color: "rgba(110,255,175,.2)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: palette.axis },
      splitLine: { lineStyle: { color: palette.line } },
    },
    series: [{
      type: "line",
      smooth: true,
      data: values,
      symbolSize: 8,
      lineStyle: { width: 4, color },
      itemStyle: { color },
      areaStyle: { color: `${color}22` },
    }],
  });
}

function setPie(id, rows, nameKey, valueKey, colors) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    color: colors,
    tooltip: { trigger: "item" },
    series: [{
      type: "pie",
      radius: ["46%", "72%"],
      center: ["50%", "48%"],
      label: { show: false },
      labelLine: { show: false },
      data: rows.map((row) => ({ name: row[nameKey], value: Number(row[valueKey] || 0) })),
    }],
  });
}

function renderKpis() {
  const cards = state.frontend?.home?.cards || {};
  const cityRows = state.flow?.forecast?.city_7day || [];
  const predictedCities = new Set(cityRows.map((row) => row.city_name).filter(Boolean)).size;
  const maxFlow = Math.max(...cityRows.map((row) => Number(row.forecast_flow || 0)), 0);
  const commentCount = Number(state.portrait?.interaction?.comment_count || 0);

  const items = [
    ["景点总量", cards.poi_total || 0],
    ["覆盖城市", cards.city_total || 0],
    ["覆盖省份", cards.province_total || 0],
    ["预测城市", predictedCities],
    ["最高预测客流", maxFlow],
    [state.role === "operator" ? "用户评论数" : "高评分景点", state.role === "operator" ? commentCount : cards.high_score_poi_total || 0],
  ];

  $("screenKpis").innerHTML = items.map(([label, value]) => `
    <div class="kpi-card">
      <label>${html(label)}</label>
      <strong>${fmt(value)}</strong>
    </div>
  `).join("");
}

function renderHeatMap() {
  const chart = state.charts.screenHeatMapChart;
  if (!chart) return;
  const rows = state.frontend?.home?.heatmap_points || [];
  const maxValue = Math.max(...rows.map((row) => Number(row.value || 0)), 1);
  chart.setOption({
    ...baseChart(),
    tooltip: {
      formatter: (p) => `${p.data.name}<br>景点数：${fmt(p.data.value[2])}<br>平均热度：${dec(p.data.heat, 1)}<br>平均评分：${dec(p.data.score, 1)}`,
    },
    grid: { left: 40, right: 20, top: 16, bottom: 28 },
    xAxis: {
      type: "value",
      min: 113,
      max: 123,
      name: "经度",
      nameTextStyle: { color: palette.axis },
      axisLabel: { color: palette.axis },
      splitLine: { lineStyle: { color: palette.line } },
    },
    yAxis: {
      type: "value",
      min: 23,
      max: 38,
      name: "纬度",
      nameTextStyle: { color: palette.axis },
      axisLabel: { color: palette.axis },
      splitLine: { lineStyle: { color: palette.line } },
    },
    visualMap: {
      min: 0,
      max: maxValue,
      right: 10,
      top: 10,
      calculable: true,
      textStyle: { color: palette.axis },
      inRange: { color: ["#123825", "#23985b", "#65ff9c"] },
    },
    series: [{
      type: "effectScatter",
      coordinateSystem: "cartesian2d",
      data: rows.map((row) => ({
        name: row.name,
        value: [Number(row.lng || 0), Number(row.lat || 0), Number(row.value || 0)],
        heat: Number(row.heat || 0),
        score: Number(row.score || 0),
      })),
      symbolSize: (value) => Math.max(8, Math.min(42, Math.sqrt(Number(value[2] || 0)) * 2.5)),
      rippleEffect: { brushType: "stroke", scale: 2.2 },
      label: { show: false },
      itemStyle: { color: "#65ff9c", shadowBlur: 18, shadowColor: "rgba(101,255,156,.28)" },
    }],
  });
}

function renderRanking() {
  const rows = (state.frontend?.detail_rankings?.hot_top20 || [])
    .slice()
    .sort((a, b) => Number(b.heat_score || 0) - Number(a.heat_score || 0))
    .slice(0, 10);
  setBar("screenRankingChart", rows.map((row) => row.poi_name || "-"), rows.map((row) => Number(row.heat_score || 0)), [palette.amber, palette.green]);
}

function topForecastCity() {
  const rows = state.flow?.forecast?.city_7day || [];
  const bucket = new Map();
  rows.forEach((row) => {
    const key = row.city_name || "";
    const value = Number(row.forecast_flow || 0);
    bucket.set(key, Math.max(bucket.get(key) || 0, value));
  });
  return [...bucket.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || "";
}

function renderFlowTrend() {
  const cityName = topForecastCity();
  const rows = (state.flow?.forecast?.city_7day || [])
    .filter((row) => row.city_name === cityName)
    .sort((a, b) => String(a.forecast_date).localeCompare(String(b.forecast_date)));
  $("screenFlowTitle").textContent = cityName ? `${cityName}未来 7 天客流` : "重点城市未来 7 天客流";
  setLine("screenFlowTrendChart", rows.map((row) => formatShortDate(row.forecast_date)), rows.map((row) => Number(row.forecast_flow || 0)), palette.cyan);
}

function renderInsight() {
  if (state.role === "operator" && state.portrait?.preferences?.length) {
    const rows = state.portrait.preferences.slice(0, 8);
    $("screenInsightTitle").textContent = "用户偏好主题";
    $("screenInsightSub").textContent = "来自收藏、评论和用户画像统计";
    $("screenInsightTag").textContent = "用户行为";
    setBar("screenInsightChart", rows.map((row) => row.preference_tag || "-"), rows.map((row) => Number(row.user_count || 0)), [palette.green, palette.cyan]);
    return;
  }

  const rows = (state.frontend?.home?.tag_top20 || []).slice(0, 8);
  $("screenInsightTitle").textContent = "热门主题画像";
  $("screenInsightSub").textContent = "游客更关注的高频景点主题";
  $("screenInsightTag").textContent = "热门标签";
  setBar("screenInsightChart", rows.map((row) => row.tag_name || "-"), rows.map((row) => Number(row.poi_count || 0)), [palette.green, palette.cyan]);
}

function renderClusters() {
  const rows = (state.flow?.clusters?.summary || []).slice();
  if (!rows.length) {
    $("screenClusterList").innerHTML = `<div class="screen-empty">暂无城市分群数据</div>`;
    return;
  }

  setPie("screenClusterChart", rows, "cluster_name", "city_count", ["#65ff9c", "#59ffd7", "#d5ff68", "#84c9ff"]);
  $("screenClusterList").innerHTML = rows.map((row) => `
    <article class="cluster-item">
      <strong>${html(row.cluster_name || "-")}</strong>
      <p>${html(row.description || "暂无说明")}</p>
      <small>城市数 ${fmt(row.city_count)} · 平均客流 ${fmt(row.avg_flow)}</small>
    </article>
  `).join("");
}

function renderAlerts() {
  const rows = (state.flow?.forecast?.future_peak_top10 || state.flow?.forecast?.future_7day || [])
    .slice()
    .sort((a, b) => Number(b.forecast_flow || 0) - Number(a.forecast_flow || 0))
    .slice(0, 8);

  $("screenAlertBody").innerHTML = rows.length
    ? rows.map((row) => `
      <tr>
        <td>${html(row.city_name || "-")}</td>
        <td>${html(row.poi_name || "-")}</td>
        <td>${html(formatShortDate(row.forecast_date))}</td>
        <td>${fmt(row.forecast_flow)}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="4">暂无高峰预警数据</td></tr>`;
}

function renderNews() {
  const rows = state.homeNews || [];
  $("screenNewsStatus").textContent = rows.length ? `已更新 ${formatNewsTime(state.homeNewsUpdatedAt)}` : "当前没有旅游公告";
  $("screenNewsBoard").innerHTML = rows.length
    ? rows.slice(0, 6).map((row) => `
      <a class="screen-news-item" href="${html(row.link || "#")}" target="_blank" rel="noreferrer">
        <strong>${html(row.title || "-")}</strong>
        <p>${html(row.summary || "点击查看完整内容")}</p>
        <small>${html(row.source || "实时新闻")}</small>
        <time>${html(formatNewsTime(row.published_at))}</time>
      </a>
    `).join("")
    : `<div class="screen-empty">暂无旅游公告</div>`;
}

async function loadNews() {
  try {
    const data = await fetchJson("/api/home-news");
    state.homeNews = data.items || [];
    state.homeNewsUpdatedAt = data.updated_at || "";
  } catch {
    state.homeNews = [];
    state.homeNewsUpdatedAt = "";
  }
  renderNews();
}

function updateClock() {
  $("screenClock").textContent = new Date().toLocaleString("zh-CN", { hour12: false });
}

async function loadWeather(lat, lon) {
  try {
    const data = await fetchJson(`/api/weather/current?lat=${lat}&lon=${lon}`);
    $("screenLocation").textContent = data.location || `${Number(lat).toFixed(3)}, ${Number(lon).toFixed(3)}`;
    if (data.temperature === null || data.temperature === undefined) {
      $("screenWeather").textContent = "天气不可用";
      return;
    }
    $("screenWeather").textContent = `${data.weather ? `${data.weather} · ` : ""}${dec(data.temperature, 1)}℃`;
  } catch {
    $("screenWeather").textContent = "天气不可用";
  }
}

function startLiveInfo() {
  updateClock();
  setInterval(updateClock, 1000);

  if (!navigator.geolocation) {
    $("screenLocation").textContent = "默认上海";
    loadWeather(31.2304, 121.4737);
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => loadWeather(pos.coords.latitude, pos.coords.longitude),
    () => {
      $("screenLocation").textContent = "默认上海";
      loadWeather(31.2304, 121.4737);
    },
    { timeout: 8000 }
  );
}

function currentSessionPayload() {
  if (!state.currentUser) return "";
  return JSON.stringify({
    user: state.currentUser,
    role: state.role,
    saved_at: Date.now(),
  });
}

function bindUI() {
  $("gotoModulesButton").addEventListener("click", () => {
    const payload = currentSessionPayload();
    if (payload) persistSessionPayload(payload);
    const params = new URLSearchParams();
    if (payload) params.set(SESSION_PARAM, payload);
    window.location.href = `/app/modules${params.toString() ? `?${params.toString()}` : ""}`;
  });

  $("screenLogoutButton").addEventListener("click", () => {
    clearSession();
    window.location.href = "/app/modules";
  });
}

function initCharts() {
  ["screenHeatMapChart", "screenRankingChart", "screenFlowTrendChart", "screenInsightChart", "screenClusterChart"].forEach((id) => {
    const el = $(id);
    if (el) state.charts[id] = echarts.init(el);
  });
  window.addEventListener("resize", () => Object.values(state.charts).forEach((chart) => chart?.resize()));
}

async function bootstrap() {
  if (!restoreSession()) {
    window.location.href = "/app/modules";
    return;
  }

  bindUI();
  initCharts();
  startLiveInfo();

  state.frontend = await fetchJson("/api/frontend-modules");
  state.flow = await fetchJson("/api/flow-module");
  if (state.role === "operator") {
    state.portrait = await fetchJson("/api/admin/user-portrait").catch(() => null);
  }

  renderKpis();
  renderHeatMap();
  renderRanking();
  renderFlowTrend();
  renderInsight();
  renderClusters();
  renderAlerts();
  await loadNews();
  setInterval(() => loadNews().catch(() => {}), 15 * 60 * 1000);
}

bootstrap().catch((error) => {
  document.body.innerHTML = `<div class="screen-empty" style="height:100vh">${html(error.message || "大屏加载失败")}</div>`;
});
