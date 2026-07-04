const placeholderImage = "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22400%22%3E%3Crect fill=%22%235f9a63%22 width=%22800%22 height=%22400%22/%3E%3Ctext fill=%22white%22 font-size=%2224%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3E%E6%99%AF%E7%82%B9%E5%9B%BE%E7%89%87%3C/text%3E%3C/svg%3E";
const defaultAvatar = "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22120%22%3E%3Ccircle fill=%22%235f9a63%22 cx=%2260%22 cy=%2260%22 r=%2260%22/%3E%3Ctext fill=%22white%22 font-size=%2248%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3E%E6%97%85%3C/text%3E%3C/svg%3E";
const operatorAvatar = "data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22120%22 height=%22120%22%3E%3Ccircle fill=%22%234f9f80%22 cx=%2260%22 cy=%2260%22 r=%2260%22/%3E%3Ctext fill=%22white%22 font-size=%2236%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3E%E7%AE%A1%3C/text%3E%3C/svg%3E";

const navItems = [
  { key: "home", label: "首页总览", roles: ["tourist", "operator"] },
  { key: "region", label: "区域看板", roles: ["tourist", "operator"] },
  { key: "filter", label: "景点筛选", roles: ["tourist"] },
  { key: "ranking", label: "景点榜单", roles: ["tourist", "operator"] },
  { key: "recommend", label: "个性推荐", roles: ["tourist"] },
  { key: "flow", label: "客流预测", roles: ["tourist", "operator"] },
  { key: "ai", label: "AI旅游助手", roles: ["tourist"] },
  { key: "plans", label: "我的计划", roles: ["tourist"] },
  { key: "impact", label: "天气分析", roles: ["operator"] },
  { key: "cluster", label: "省份竞争力", roles: ["operator"] },
  { key: "operator", label: "用户画像", roles: ["operator"] },
];

const navIcons = { plans: "???", home: "首页", region: "区域", filter: "筛选", ranking: "排行", recommend: "推荐", flow: "客流", ai: "AI", impact: "影响", cluster: "省份", operator: "管理员" };
const rankMap = { hot_top20: "热门榜", value_top20: "口碑榜", night_top20: "夜游榜", family_top20: "亲子榜", free_top20: "免费榜" };
const palette = { red: "#d17f63", orange: "#a9c56d", green: "#5f9a63", teal: "#4f9f80", blue: "#78ad8f", brown: "#7d9b59", rose: "#8fb77a" };
const SESSION_KEY = "travel_project_current_user";
const SESSION_COOKIE = "travel_project_session";
const SESSION_PARAM = "session";

const state = {
  role: "tourist",
  loginRole: "tourist",
  appView: "modules",
  activeModule: "home",
  activeRank: "hot_top20",
  filterSortMode: "balanced",
  regionMode: "province",
  provinceName: "",
  cityName: "",
  forecastCity: "",
  impactProvince: "",
  impactCity: "",
  impactPoi: "",
  recommendProvince: "",
  recommendCity: "",
  recommendPoi: "",
  recommendSource: "",
  recommendAlgorithm: "als",
  recommendMode: "balanced",
  currentUser: null,
  plans: [],
  activePlanId: 0,
  currentPlanDetail: null,
  latestAiPlan: null,
  planQuickEdit: false,
  favoriteIds: new Set(),
  frontend: null,
  flow: null,
  portrait: null,
  adminUsers: [],
  guideOptions: null,
  config: {},
  charts: {},
  homeNews: [],
  homeNewsUpdatedAt: "",
  carouselIndex: 0,
  activeCommentPoi: null,
  replyParentId: "",
  amap: null,
  leafletMap: null,
  leafletPromise: null,
  previewMap: null,
  previewFallbackChart: null,
  amapScriptPromise: null,
  amapReady: false,
  filterVisibleCount: 30,
};

function saveSession() {
  if (!state.currentUser) return;
  const payload = JSON.stringify({
    user: state.currentUser,
    role: state.role,
    saved_at: Date.now(),
  });
  persistSessionPayload(payload);
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

function currentSessionPayload() {
  if (!state.currentUser) return "";
  return JSON.stringify({
    user: state.currentUser,
    role: state.role,
    saved_at: Date.now(),
  });
}

function readSessionCookie() {
  try {
    const raw = String(document.cookie || "")
      .split("; ")
      .find((item) => item.startsWith(`${SESSION_COOKIE}=`));
    if (!raw) return "";
    return decodeURIComponent(raw.slice(SESSION_COOKIE.length + 1));
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
    state.loginRole = state.role;
    state.activeModule = state.role === "operator" ? "operator" : "home";
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

function goDashboardPage() {
  if (!state.currentUser) {
    openDrawer();
    return;
  }
  const payload = currentSessionPayload();
  persistSessionPayload(payload);
  const params = new URLSearchParams();
  if (payload) params.set(SESSION_PARAM, payload);
  window.location.href = `/app/dashboard${params.toString() ? `?${params.toString()}` : ""}`;
}

function $(id) {
  return document.getElementById(id);
}

function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
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

function pct(value) {
  const num = Number(value);
  return Number.isNaN(num) ? "-" : `${(num * 100).toFixed(1)}%`;
}

function metricDisplay(label, value) {
  if (label === "R²") return String(value ?? "-");
  return fmt(value);
}

function windSummary(data = {}) {
  const direction = String(data.wind_direction || "").trim();
  const power = String(data.wind_power || "").trim();
  if (power) {
    const powerText = power.includes("级") ? power : `${power}级`;
    return direction ? `${direction}风 ${powerText}` : powerText;
  }
  if (data.wind_speed !== null && data.wind_speed !== undefined && data.wind_speed !== "") {
    return `风速 ${dec(data.wind_speed, 1)} km/h`;
  }
  return "";
}

function freeRatioOf(row) {
  const poiCount = Number(row?.poi_count || 0);
  const freeCount = Number(row?.free_poi_count || 0);
  if (poiCount > 0 && freeCount >= 0) return freeCount / poiCount;
  return Number(row?.free_ratio || 0);
}

function imageOf(row) {
  const value = String(row.cover_image_url || row.coverImageUrl || "").trim();
  if (value.startsWith("//")) return `https:${value}`;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  return placeholderImage;
}

function detailOf(row) {
  const value = String(row.detail_url || row.detailUrl || "").trim();
  if (value.startsWith("//")) return `https:${value}`;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  return "#";
}

function avatarOf(user) {
  if (!user) return defaultAvatar;
  if (user.role === "operator") return operatorAvatar;
  const value = String(user.avatar_url || "").trim();
  if (value.startsWith("data:image/")) return value;
  if (value.startsWith("//")) return `https:${value}`;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  const seed = encodeURIComponent(user.username || user.nickname || "travel");
  return `https://api.dicebear.com/7.x/initials/svg?seed=${seed}`;
}

function setAvatarPreview(src) {
  $("profileAvatar").src = src;
  $("drawerAvatar").src = src;
}

function compositeScore(row) {
  const heat = Number(row.heat_score || 0);
  const score = Number(row.comment_score || 0);
  const comments = Math.min(Number(row.comment_count || 0), 50000);
  const price = Number(row.price || 0);
  const valueBonus = price <= 0 ? 3 : Math.max(0, 2 - price / 180);
  return Number(row.composite_score || (heat * 0.45 + score * 8 + comments / 5000 + valueBonus));
}

async function fetchJson(path) {
  const res = await fetch(path);
  const body = await res.json();
  if (!body.success) throw new Error(body.message || "请求失败");
  return body.data;
}

async function fetchJsonPost(path, payload = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!body.success) throw new Error(body.message || "提交失败");
  return body.data;
}

function emptyFrontendBundle() {
  return {
    manifest: {},
    home: { cards: {}, heatmap_points: [], price_distribution: [], score_distribution: [], distance_distribution: [], comment_score_distribution: [], tag_top20: [], hot_poi_top10: [] },
    region_dashboard: { province_summary: [], city_summary: [], city_tag_summary: [], city_top_poi: [], province_top_poi: [] },
    filter_panel: { options: {}, sample_poi: [] },
    detail_rankings: { summary: {}, hot_top20: [], value_top20: [], night_top20: [], family_top20: [], free_top20: [] },
    admin_dashboard: { city_summary: [], region_summary: [], tag_summary: [] },
    recommendation: { cards: [], source_options: [], algorithms: [], modes: [], report: {}, location_index: { provinces: [], cities_by_province: {}, pois_by_city: {} } },
  };
}

function emptyFlowBundle() {
  return {
    report: {},
    forecast: { future_7day: [], city_7day: [], future_peak_top10: [], test_top_error: [] },
    impact: { weather_holiday_summary: [], holiday_type_summary: [], city_impact_top20: [] },
    clusters: { summary: [], profiles: [] },
  };
}

function initCharts() {
  [
    "homeHeatMapChart",
    "homePriceChart",
    "homeTagChart",
    "homeDistanceChart",
    "homeCommentScoreChart",
    "screenHeatMapChart",
    "screenFlowTrendChart",
    "screenRankingChart",
    "screenInsightChart",
    "regionRankChart",
    "cityTagRadarChart",
    "filterScoreChart",
    "filterTagChart",
    "detailRankChart",
    "detailScoreChart",
    "recommendScoreChart",
    "forecastTrendChart",
    "aiMapBox",
    "flowImpactChart",
    "holidayTypeChart",
    "impactPoiWeatherChart",
    "impactCityRankChart",
    "clusterSummaryChart",
    "clusterProfileChart",
    "clusterTagCompareChart",
    "portraitSegmentChart",
    "portraitPreferenceChart",
    "portraitCityChart",
    "portraitAgeChart",
    "portraitWordCloudChart",
  ].forEach((id) => {
    const el = $(id);
    if (el) state.charts[id] = echarts.init(el);
  });
  window.addEventListener("resize", () => Object.values(state.charts).forEach((chart) => chart?.resize()));
}

function baseChart() {
  return { backgroundColor: "transparent", textStyle: { fontFamily: "Microsoft YaHei, PingFang SC, sans-serif", color: "#244734" } };
}

function setBar(id, names, values, horizontal = false, colors = [palette.red, palette.orange]) {
  const chart = state.charts[id];
  if (!chart) return;
  const isRecommendScore = id === "recommendScoreChart";
  chart.setOption({
    ...baseChart(),
    tooltip: { trigger: "axis" },
    grid: {
      left: horizontal ? (isRecommendScore ? 104 : 116) : 48,
      right: isRecommendScore ? 28 : 18,
      top: isRecommendScore ? 16 : 24,
      bottom: isRecommendScore ? 28 : 48,
      containLabel: true,
    },
    xAxis: horizontal ? { type: "value", splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } } } : { type: "category", data: names, axisLabel: { rotate: names.length > 7 ? 24 : 0 } },
    yAxis: horizontal ? {
      type: "category",
      data: names,
      inverse: true,
      axisLabel: { width: isRecommendScore ? 96 : 108, overflow: "truncate", margin: isRecommendScore ? 10 : 10 },
    } : { type: "value", splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } } },
    series: [{
      type: "bar",
      data: values,
      barMaxWidth: isRecommendScore ? 40 : 30,
      itemStyle: {
        borderRadius: horizontal ? [0, 12, 12, 0] : [12, 12, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, horizontal ? 1 : 0, horizontal ? 0 : 1, [{ offset: 0, color: colors[0] }, { offset: 1, color: colors[1] || colors[0] }]),
      },
    }],
  });
}

function setBarCompact(id, names, values, colors = [palette.blue, palette.teal]) {
  const chart = state.charts[id];
  if (!chart) return;
  const rowCount = Math.max(names.length, 1);
  const chartHeight = Math.max(360, rowCount * 34);
  const el = document.getElementById(id);
  if (el) el.style.height = `${chartHeight}px`;
  chart.setOption({
    ...baseChart(),
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter(params) {
        const item = params?.[0];
        return item ? `${item.name}<br>热度：${dec(item.value, 1)}` : "";
      },
    },
    grid: { left: 210, right: 42, top: 24, bottom: 26, containLabel: false },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } } },
    yAxis: {
      type: "category",
      data: names,
      axisLabel: {
        width: 180,
        lineHeight: 18,
        overflow: "truncate",
        margin: 18,
      },
      axisTick: { show: false },
    },
    series: [{
      type: "bar",
      data: values,
      barMaxWidth: 22,
      barCategoryGap: "38%",
      itemStyle: {
        borderRadius: [0, 12, 12, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: colors[0] }, { offset: 1, color: colors[1] || colors[0] }]),
      },
      label: {
        show: true,
        position: "right",
        color: "#406852",
        formatter: ({ value }) => dec(value, 1),
      },
    }],
  });
}

function setLine(id, names, values, color = palette.red) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    tooltip: { trigger: "axis" },
    grid: { left: 60, right: 22, top: 24, bottom: 44 },
    xAxis: { type: "category", data: names },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } } },
    series: [{ type: "line", smooth: true, data: values, symbolSize: 9, lineStyle: { width: 4, color }, itemStyle: { color }, areaStyle: { color: `${color}22` } }],
  });
}

function setPie(id, rows, nameKey, valueKey, colors = [palette.red, palette.orange, palette.green, palette.blue, palette.brown]) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    tooltip: { trigger: "item" },
    color: colors,
    legend: { bottom: 0, textStyle: { color: "#64806b" } },
    series: [{ type: "pie", radius: ["42%", "70%"], center: ["50%", "42%"], data: rows.map((row) => ({ name: row[nameKey], value: row[valueKey] })), label: { color: "#244734" } }],
  });
}

function setDistanceLevelChart(id, rows, nameKey, valueKey) {
  const chart = state.charts[id];
  if (!chart) return;
  const colorMap = {
    "市中心": "#4c9f70",
    "近郊": "#2b7f77",
    "远郊": "#86b84b",
    "未知距离": "#b46f2d",
  };
  const data = rows
    .map((row) => ({
      name: row[nameKey],
      value: Number(row[valueKey] || 0),
    }))
    .filter((row) => row.name && row.value > 0)
    .sort((a, b) => b.value - a.value)
    .map((row) => ({
      ...row,
      itemStyle: {
        color: colorMap[row.name] || palette.green,
      },
    }));
  chart.setOption({
    ...baseChart(),
    tooltip: {
      trigger: "item",
      formatter: (params) => `${params.name}<br>景点数：${fmt(params.value)}<br>占比：${dec(params.percent, 1)}%`,
    },
    legend: {
      bottom: 6,
      icon: "roundRect",
      itemWidth: 18,
      itemHeight: 12,
      textStyle: { color: "#5f765f", fontSize: 14 },
    },
    series: [{
      name: "距离级别",
      type: "pie",
      radius: [24, "74%"],
      center: ["50%", "47%"],
      startAngle: 90,
      clockwise: true,
      minAngle: 4,
      padAngle: 2,
      selectedOffset: 12,
      roseType: "area",
      itemStyle: {
        borderRadius: 18,
        borderColor: "rgba(255,255,255,.9)",
        borderWidth: 3,
        shadowBlur: 10,
        shadowColor: "rgba(83,125,88,.12)",
      },
      label: {
        show: true,
        color: "#2f4b38",
        fontSize: 18,
        fontWeight: 500,
        formatter: "{b}",
      },
      labelLine: {
        show: true,
        length: 26,
        length2: 30,
        smooth: 0.18,
        lineStyle: { width: 2, color: "inherit" },
      },
      emphasis: {
        scale: true,
        scaleSize: 10,
      },
      data,
    }],
  });
}

function setRosePie(id, rows, nameKey, valueKey, colors = [palette.green, palette.teal, "#96c76a", "#f0b35a", "#d5e7c4"]) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    tooltip: {
      trigger: "item",
      formatter: (params) => `${params.name}<br>景点数：${fmt(params.value)}<br>占比：${dec(params.percent, 1)}%`,
    },
    color: colors,
    legend: { bottom: 0, textStyle: { color: "#64806b" } },
    series: [{
      type: "pie",
      roseType: "radius",
      radius: ["22%", "72%"],
      center: ["50%", "42%"],
      itemStyle: { borderRadius: 10, borderColor: "rgba(255,255,255,.85)", borderWidth: 2 },
      label: { color: "#244734" },
      data: rows.map((row) => ({ name: row[nameKey], value: row[valueKey] })),
    }],
  });
}

function setScatter(id, rows, xFn, yFn, sizeFn, xName, yName, color = palette.green) {
  const chart = state.charts[id];
  if (!chart) return;
  const nameField = id === "clusterProfileChart" ? "province" : null;
  const isProvinceChart = id === "clusterProfileChart";
  const xValues = rows.map((row) => Number(xFn(row))).filter((value) => Number.isFinite(value));
  const yValues = rows.map((row) => Number(yFn(row))).filter((value) => Number.isFinite(value));
  const isProvinceCompetition = isProvinceChart && xValues.length && yValues.length;
  const xMin = isProvinceCompetition ? Math.max(0, Math.floor((Math.min(...xValues) - 0.25) * 10) / 10) : null;
  const xMax = isProvinceCompetition ? Math.ceil((Math.max(...xValues) + 0.25) * 10) / 10 : null;
  const yMin = isProvinceCompetition ? Math.max(0, Math.floor((Math.min(...yValues) - 0.15) * 10) / 10) : null;
  const yMax = isProvinceCompetition ? Math.min(5, Math.ceil((Math.max(...yValues) + 0.15) * 10) / 10) : null;
  const seriesData = rows.map((row) => ({
    value: [xFn(row), yFn(row), sizeFn(row)],
    rawSize: isProvinceChart ? Number(row.poiCount || row.poi_count || 0) : Number(sizeFn(row) || 0),
  }));
  chart.setOption({
    ...baseChart(),
    tooltip: {
      formatter(params) {
        const row = rows[params.dataIndex] || {};
        const sizeLabel = isProvinceChart ? "景点数" : "规模";
        const sizeValue = params.data?.rawSize ?? params.value?.[2];
        return `${html((nameField && row[nameField]) || row.poi_name || row.city_name || row.name)}<br>${xName}: ${dec(params.value[0], 1)}<br>${yName}: ${dec(params.value[1], 1)}<br>${sizeLabel}: ${fmt(sizeValue)}`;
      },
    },
    grid: { left: 70, right: 34, top: 42, bottom: 54, containLabel: false },
    xAxis: {
      type: "value",
      name: xName,
      min: xMin,
      max: xMax,
      nameLocation: "end",
      nameGap: 12,
      nameTextStyle: { align: "right", verticalAlign: "top", padding: [10, 0, 0, 0] },
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    yAxis: {
      type: "value",
      name: yName,
      min: yMin,
      max: yMax,
      nameLocation: "end",
      nameGap: 18,
      nameTextStyle: { align: "left", padding: [0, 0, 8, 0] },
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    series: [{
      type: "scatter",
      data: seriesData,
      symbolSize: (value) => {
        const scale = isProvinceChart ? 220 : 360;
        const minSize = isProvinceChart ? 20 : 12;
        const maxSize = isProvinceChart ? 62 : 46;
        return Math.max(minSize, Math.min(maxSize, Number(value[2]) / scale));
      },
      itemStyle: { color, opacity: 0.78 },
    }],
  });
}

function setRankingScatter(id, rows) {
  const chart = state.charts[id];
  if (!chart) return;
  if (!rows.length) {
    chart.clear();
    return;
  }
  const rawX = rows.map((row) => Number(row.comment_score || 0)).filter((value) => Number.isFinite(value) && value > 0);
  const rawY = rows.map((row) => Number(row.heat_score || 0)).filter((value) => Number.isFinite(value) && value > 0);
  const avgScore = rawX.reduce((sum, value) => sum + value, 0) / Math.max(rawX.length, 1);
  const avgHeat = rawY.reduce((sum, value) => sum + value, 0) / Math.max(rawY.length, 1);
  const minScore = Math.max(3.6, Math.floor((Math.min(...rawX) - 0.15) * 10) / 10);
  const maxScore = Math.min(5, Math.ceil((Math.max(...rawX) + 0.1) * 10) / 10);
  const minHeat = Math.max(4.5, Math.floor((Math.min(...rawY) - 0.5) * 10) / 10);
  const maxHeat = Math.min(10, Math.ceil((Math.max(...rawY) + 0.4) * 10) / 10);
  const grouped = new Map();
  const points = rows.map((row, index) => {
    const x = Number(row.comment_score || 0);
    const y = Number(row.heat_score || 0);
    const key = `${x.toFixed(2)}_${y.toFixed(2)}`;
    const group = grouped.get(key) || [];
    group.push(index);
    grouped.set(key, group);
    return { row, x, y, size: Number(row.comment_count || 0), index };
  });
  grouped.forEach((indexes) => {
    if (indexes.length <= 1) return;
    indexes.forEach((pointIndex, order) => {
      const angle = (Math.PI * 2 * order) / indexes.length;
      const radius = 0.05 + Math.floor(order / 6) * 0.04;
      points[pointIndex].x = Math.max(0, Math.min(5, points[pointIndex].x + Math.cos(angle) * radius));
      points[pointIndex].y = Math.max(0, Math.min(10, points[pointIndex].y + Math.sin(angle) * radius));
    });
  });
  chart.setOption({
    ...baseChart(),
    tooltip: {
      formatter(params) {
        const point = points[params.dataIndex];
        const row = point?.row || {};
        const score = Number(row.comment_score || 0);
        const heat = Number(row.heat_score || 0);
        const commentCount = Number(row.comment_count || 0);
        const quadrant = score >= avgScore && heat >= avgHeat
          ? "高分高热"
          : score >= avgScore && heat < avgHeat
            ? "高分潜力型"
            : score < avgScore && heat >= avgHeat
              ? "高热争议型"
              : "基础稳定型";
        return `${html(row.poi_name || "-")}<br>城市：${html(row.city_name || "-")}<br>评分：${dec(score, 1)}<br>热度：${dec(heat, 1)}<br>评论数：${fmt(commentCount)}<br>当前定位：${quadrant}`;
      },
    },
    grid: { left: 44, right: 54, top: 44, bottom: 48 },
    xAxis: {
      type: "value",
      name: "评分",
      min: minScore,
      max: maxScore,
      interval: 0.2,
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
      axisLabel: { formatter: (value) => Number(value).toFixed(1) },
    },
    yAxis: {
      type: "value",
      name: "热度",
      min: minHeat,
      max: maxHeat,
      interval: 0.5,
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    series: [{
      type: "scatter",
      data: points.map((point) => [point.x, point.y, point.size]),
      symbolSize: (value) => Math.max(14, Math.min(38, Math.sqrt(Number(value[2]) || 0) / 5)),
      itemStyle: {
        color(params) {
          const row = rows[params.dataIndex] || {};
          const score = Number(row.comment_score || 0);
          const heat = Number(row.heat_score || 0);
          if (score >= avgScore && heat >= avgHeat) return "#68a850";
          if (score >= avgScore && heat < avgHeat) return "#4fa49b";
          if (score < avgScore && heat >= avgHeat) return "#f0a851";
          return "#8ba3d7";
        },
        opacity: 0.82,
        shadowBlur: 14,
        shadowColor: "rgba(112,171,70,.22)",
      },
      markLine: {
        silent: true,
        symbol: "none",
        lineStyle: { color: "rgba(92,135,104,.38)", type: "dashed", width: 1.4 },
        data: [
          { xAxis: avgScore },
          { yAxis: avgHeat },
        ],
        label: {
          color: "#6a836f",
          formatter(params) {
            return "均价";
          },
        },
      },
    }],
  });
}

function buildNav() {
  const visibleItems = navItems.filter((item) => item.roles.includes(state.role));
  $("moduleSwitches").style.setProperty("--nav-count", visibleItems.length);
  $("moduleSwitches").innerHTML = visibleItems
    .map((item) => `<button class="module-switch ${item.key === state.activeModule ? "active" : ""}" data-module="${item.key}"><b>${navIcons[item.key]}</b><span>${item.label}</span></button>`)
    .join("");
  $("moduleSwitches").classList.toggle("dense-nav", document.querySelectorAll(".module-switch").length > 7);
  document.querySelectorAll(".module-switch").forEach((btn) => btn.addEventListener("click", () => {
    state.activeModule = btn.dataset.module;
    document.querySelector(".side-nav")?.classList.remove("menu-open");
    switchModule();
  }));
}

function updateViewSwitches() {
  document.querySelectorAll("[data-app-view]").forEach((btn) => btn.classList.toggle("active", btn.dataset.appView === state.appView));
}

function switchModule() {
  const allowed = navItems.filter((item) => item.roles.includes(state.role)).map((item) => item.key);
  if (!allowed.includes(state.activeModule)) state.activeModule = allowed[0];
  document.querySelectorAll(".module-panel").forEach((panel) => panel.classList.toggle("active", panel.dataset.module === state.activeModule));
  if (state.appView === "modules") {
    $("pageTitle").textContent = navItems.find((item) => item.key === state.activeModule)?.label || "首页总览";
  }
  buildNav();
  if (state.activeModule === "plans") {
    renderPlans();
  }
  if (state.activeModule === "operator" && state.currentUser?.role === "operator") {
    renderPortrait(true).catch((e) => console.warn(e));
  }
  if (state.activeModule === "impact") {
    renderImpact();
  }
  if (state.activeModule === "ai" && state.latestAiPlan) {
    if (state.config.amap_key && !window.AMap) loadAmapScript().catch(() => {});
    setTimeout(() => renderAiMap(state.latestAiPlan?.pois || []), 60);
    setTimeout(() => renderAiMap(state.latestAiPlan?.pois || []), 260);
    setTimeout(() => renderAiMap(state.latestAiPlan?.pois || []), 620);
  }
  requestVisualRefresh();
}

function switchAppView(view) {
  if (!$("dashboardPanel")) return;
  state.appView = view === "modules" ? "modules" : "dashboard";
  $("dashboardPanel")?.classList.toggle("hidden", state.appView !== "dashboard");
  $("moduleContent")?.classList.toggle("hidden", state.appView !== "modules");
  $("appShell")?.classList.toggle("dashboard-mode", state.appView === "dashboard");
  updateViewSwitches();
  if (state.appView === "dashboard") {
    $("pageTitle").textContent = "数据大屏";
    renderBigScreen();
  } else {
    switchModule();
  }
  requestVisualRefresh(true);
}

function enterApp(role) {
  state.role = role;
  state.loginRole = role;
  $("loginUsername").value = role === "operator" ? "operator" : "tourist";
  $("loginPassword").value = "123456";
  document.querySelectorAll(".login-role").forEach((btn) => btn.classList.toggle("active", btn.dataset.loginRole === role));
  $("showRegisterButton").classList.toggle("hidden", role === "operator");
  showLogin();
  openDrawer();
}

function showAppAfterAuth(deferRender = false) {
  if (!state.currentUser) {
    $("appShell").classList.add("hidden");
    $("welcomeScreen").classList.remove("hidden");
    openDrawer();
    return;
  }
  $("welcomeScreen").classList.add("hidden");
  $("appShell").classList.remove("hidden");
  closeDrawer();
  buildNav();
  if (deferRender) {
    const allowed = navItems.filter((item) => item.roles.includes(state.role)).map((item) => item.key);
    if (!allowed.includes(state.activeModule)) state.activeModule = allowed[0];
    document.querySelectorAll(".module-panel").forEach((panel) => panel.classList.toggle("active", panel.dataset.module === state.activeModule));
    if (state.appView === "modules") {
      $("pageTitle").textContent = navItems.find((item) => item.key === state.activeModule)?.label || "首页总览";
    }
    updateViewSwitches();
    requestVisualRefresh(true);
    return;
  }
  switchModule();
  requestVisualRefresh(true);
}

function returnWelcome() {
  $("appShell").classList.add("hidden");
  $("welcomeScreen").classList.remove("hidden");
  closeDrawer();
  state.currentUser = null;
  state.favoriteIds = new Set();
  state.plans = [];
  state.activePlanId = 0;
  state.currentPlanDetail = null;
  state.latestAiPlan = null;
  state.planQuickEdit = false;
  state.appView = "modules";
  state.activeModule = "home";
  $("moduleSwitches").innerHTML = "";
  updateProfileUI();
  clearSession();
  updateViewSwitches();
}

function rerenderVisibleModule() {
  const current = state.activeModule;
  if (current === "home") renderHome();
  else if (current === "region") renderRegion();
  else if (current === "filter") renderFilter();
  else if (current === "ranking") renderRanking();
  else if (current === "recommend") renderRecommend();
  else if (current === "flow") renderFlow();
  else if (current === "ai") {
    if (state.config.amap_key && !window.AMap) loadAmapScript().catch(() => {});
    renderAiMap(state.latestAiPlan?.pois || []);
  }
  else if (current === "impact") renderImpact();
  else if (current === "cluster") renderCluster();
  else if (current === "plans") renderPlans();
  else if (current === "operator" && state.currentUser?.role === "operator") renderPortrait(true).catch(() => {});
}

function requestVisualRefresh(forceRerender = false) {
  const run = () => {
    Object.values(state.charts).forEach((chart) => chart?.resize());
    if (forceRerender) rerenderVisibleModule();
  };
  requestAnimationFrame(() => requestAnimationFrame(run));
  setTimeout(run, 180);
  setTimeout(run, 420);
}

function scenicCards(rows, limit = 8, options = {}) {
  const showDesc = options.showDesc !== false;
  return rows.slice(0, limit).map((row) => {
    const poiId = row.poi_id || row.target_poi_id || "";
    const favored = state.favoriteIds.has(String(poiId));
    const price = Number(row.price || 0) > 0 ? `¥${dec(row.price, 0)}` : "免费";
    const detailUrl = detailOf(row);
    return `
      <article class="poi-card">
        <a href="${html(detailUrl)}" target="_blank" rel="noreferrer"><img src="${html(imageOf(row))}" alt="${html(row.poi_name || "景点")}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='${placeholderImage}'"></a>
        <div class="poi-body">
          <div class="poi-title"><h3>${html(row.poi_name || "-")}</h3><span>${price}</span></div>
          <p>${html(row.city_name || "-")} / ${html(row.region_name || row.district_name || "景区")}</p>
          ${showDesc ? `<p class="desc">${html(row.reason_text || row.short_feature || "适合收藏、评论和出行决策")}</p>` : ""}
          <div class="poi-meta"><span>评分 ${dec(row.comment_score || 0)}</span><span>热度 ${dec(row.heat_score || 0)}</span><span>评论 ${fmt(row.comment_count || 0)}</span></div>
          <div class="poi-actions">
            <button class="heart-button ${favored ? "active" : ""}" data-fav="${html(poiId)}" data-name="${html(row.poi_name || "")}" data-city="${html(row.city_name || "")}" title="${favored ? "取消收藏" : "收藏"}">${favored ? "❤️" : "♡"}</button>
            <button data-comment="${html(poiId)}" data-name="${html(row.poi_name || "")}" data-city="${html(row.city_name || "")}">评论</button>
          </div>
        </div>
      </article>`;
  }).join("");
}

function bindCardActions(root = document) {
  root.querySelectorAll(".poi-actions").forEach((wrap) => {
    if (wrap.querySelector("[data-preview]")) return;
    const commentBtn = wrap.querySelector("[data-comment]");
    if (!commentBtn) return;
    const previewBtn = document.createElement("button");
    previewBtn.textContent = "查看位置";
    previewBtn.dataset.preview = commentBtn.dataset.comment || "";
    previewBtn.dataset.name = commentBtn.dataset.name || "";
    previewBtn.dataset.city = commentBtn.dataset.city || "";
    wrap.insertBefore(previewBtn, wrap.children[1] || commentBtn);
  });
  root.querySelectorAll("[data-preview]").forEach((btn) => {
    btn.addEventListener("click", () => openPreviewModalFromButton(btn).catch((e) => alert(e.message)));
  });
  root.querySelectorAll("[data-fav]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!state.currentUser) return openDrawer();
      const poiId = String(btn.dataset.fav || "");
      if (!poiId) return;
      if (state.favoriteIds.has(poiId)) {
        await fetchJson(`/api/user/remove-favorite?user_id=${state.currentUser.id}&poi_id=${poiId}`);
        state.favoriteIds.delete(poiId);
      } else {
        await fetchJson(`/api/user/add-favorite?user_id=${state.currentUser.id}&poi_id=${poiId}&poi_name=${encodeURIComponent(btn.dataset.name || "")}&city_name=${encodeURIComponent(btn.dataset.city || "")}`);
        state.favoriteIds.add(poiId);
      }
      await loadFavorites();
      refreshFavoriteButtons();
    });
  });
  root.querySelectorAll("[data-comment]").forEach((btn) => btn.addEventListener("click", () => openCommentModal({ poi_id: btn.dataset.comment, poi_name: btn.dataset.name, city_name: btn.dataset.city })));
  refreshFavoriteButtons(root);
}

async function loadPoiPreview(poiId, poiName = "", cityName = "") {
  const params = new URLSearchParams();
  if (poiId) params.set("poi_id", poiId);
  if (poiName) params.set("poi_name", poiName);
  if (cityName) params.set("city_name", cityName);
  return fetchJson(`/api/poi/preview?${params.toString()}`);
}

function destroyPreviewMap() {
  if (state.previewMap && typeof state.previewMap.destroy === "function") state.previewMap.destroy();
  state.previewMap = null;
  if (state.previewFallbackChart) state.previewFallbackChart.dispose();
  state.previewFallbackChart = null;
  const box = $("previewMapBox");
  if (box) box.innerHTML = "";
}

function closePreviewModal() {
  $("previewModal")?.classList.add("hidden");
  destroyPreviewMap();
}

function ensurePreviewModalMarkup() {
  const modal = $("previewModal");
  if (!modal) return;
  if ($("previewMapBox") && $("previewAmapLink") && $("previewModeNote")) return;
  modal.innerHTML = `
    <div class="preview-panel location-panel">
      <div class="drawer-head">
        <div>
          <p class="eyebrow">LOCATION</p>
          <h2 id="previewPoiName">景点位置查看</h2>
        </div>
        <button class="icon-button" id="previewClose">×</button>
      </div>
      <div class="preview-layout location-layout">
        <div class="preview-map-frame">
          <div class="preview-map" id="previewMapBox"></div>
        </div>
        <div class="preview-side">
          <div class="preview-meta">
            <div class="preview-meta-item"><span>城市</span><strong id="previewCity">-</strong></div>
            <div class="preview-meta-item"><span>区域</span><strong id="previewRegion">-</strong></div>
            <div class="preview-meta-item"><span>标签</span><strong id="previewTags">-</strong></div>
            <div class="preview-meta-item"><span>坐标</span><strong id="previewCoords">-</strong></div>
          </div>
          <div class="preview-note" id="previewModeNote">可直接在地图中拖动、缩放查看景点所在位置和周边环境</div>
          <div class="preview-link-grid single-link">
            <a id="previewAmapLink" target="_blank" rel="noreferrer">在高德中打开</a>
          </div>
        </div>
      </div>
    </div>
  `;
}

async function renderPoiPreviewMap(payload) {
  ensurePreviewModalMarkup();
  const box = $("previewMapBox");
  const modeNote = $("previewModeNote");
  if (!box) return;
  destroyPreviewMap();
  box.innerHTML = "";
  if (!payload?.has_coordinate) {
    box.innerHTML = `<div class="preview-empty">当前景点缺少坐标，暂时无法展示地图位置</div>`;
    if (modeNote) modeNote.textContent = "当前景点缺少坐标，暂时只能查看基础信息";
    return;
  }
  if (state.config.amap_key) {
    try {
      await loadAmapScript();
      if (window.AMap) {
        state.previewMap = new AMap.Map(box, {
          zoom: 16,
          center: [payload.longitude, payload.latitude],
          viewMode: "3D",
          pitch: 28,
          mapStyle: "amap://styles/fresh",
          resizeEnable: true,
          dragEnable: true,
          zoomEnable: true,
          scrollWheel: true,
        });
        try {
          state.previewMap.addControl(new AMap.Scale());
          state.previewMap.addControl(new AMap.ToolBar());
        } catch {}
        const marker = new AMap.Marker({
          position: [payload.longitude, payload.latitude],
          title: payload.poi_name || "景点",
          label: { content: payload.poi_name || "景点", direction: "top" },
        });
        const circle = new AMap.Circle({
          center: [payload.longitude, payload.latitude],
          radius: 600,
          strokeColor: "#5f9a63",
          strokeWeight: 2,
          fillColor: "#8dcf98",
          fillOpacity: 0.16,
        });
        state.previewMap.add([marker, circle]);
        state.previewMap.setFitView([marker, circle], false, [36, 36, 36, 36]);
        setTimeout(() => state.previewMap?.resize?.(), 60);
        setTimeout(() => state.previewMap?.resize?.(), 220);
        if (modeNote) modeNote.textContent = "当前位置已在高德地图中标注，可直接拖动、缩放查看景点和周边环境";
        return;
      }
    } catch (error) {
      console.warn("preview amap failed", error);
    }
  }
  state.previewFallbackChart = echarts.init(box);
  state.previewFallbackChart.setOption({
    ...baseChart(),
    grid: { left: 50, right: 24, top: 20, bottom: 42 },
    tooltip: {
      formatter() {
        return [
          `<strong>${html(payload.poi_name || "景点")}</strong>`,
          `经度：{dec(payload.longitude, 6)}`,
          `纬度：{dec(payload.latitude, 6)}`,
          payload.tag_text ? `标签：{html(payload.tag_text)}` : "",
        ].filter(Boolean).join("<br>");
      },
    },
    xAxis: {
      type: "value",
      min: Number(payload.longitude) - 0.03,
      max: Number(payload.longitude) + 0.03,
      axisLabel: { formatter: (v) => Number(v).toFixed(2) },
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    yAxis: {
      type: "value",
      min: Number(payload.latitude) - 0.02,
      max: Number(payload.latitude) + 0.02,
      axisLabel: { formatter: (v) => Number(v).toFixed(2) },
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    series: [{
      type: "effectScatter",
      symbolSize: 20,
      rippleEffect: { scale: 4, brushType: "stroke" },
      itemStyle: { color: "#5f9a63" },
      data: [{ name: payload.poi_name || "景点", value: [Number(payload.longitude), Number(payload.latitude)] }],
    }],
  });
  if (modeNote) modeNote.textContent = "当前无法加载在线地图，已切换为坐标定位视图";
}

function buildAmapPreviewUrl(payload) {
  if (!payload?.has_coordinate) return "#";
  const name = encodeURIComponent(payload.poi_name || "景点");
  return `https://uri.amap.com/marker?position=${payload.longitude},${payload.latitude}&name=${name}&coordinate=gaode&callnative=0`;
}

async function openPreviewModalFromButton(btn) {
  ensurePreviewModalMarkup();
  const payload = await loadPoiPreview(btn.dataset.preview || "", btn.dataset.name || "", btn.dataset.city || "");
  $("previewPoiName").textContent = `${payload.poi_name || "景点"} 位置查看`;
  $("previewCity").textContent = payload.city_name || payload.province || "-";
  $("previewRegion").textContent = payload.region_name || payload.province || "-";
  $("previewTags").textContent = payload.tag_text || "暂无标签";
  $("previewCoords").textContent = payload.has_coordinate ? `${dec(payload.longitude, 6)}, ${dec(payload.latitude, 6)}` : "暂无坐标";
  $("previewModeNote").textContent = payload.has_coordinate
    ? "正在加载高德地图位置视图，请稍候"
    : "当前景点缺少坐标，暂时只能查看基础信息";
  const amapLink = $("previewAmapLink");
  amapLink.href = buildAmapPreviewUrl(payload);
  amapLink.classList.toggle("hidden", !payload.has_coordinate);
  $("previewModal").classList.remove("hidden");
  await renderPoiPreviewMap(payload);
}

function refreshFavoriteButtons(root = document) {
  root.querySelectorAll("[data-fav]").forEach((btn) => {
    const favored = state.favoriteIds.has(String(btn.dataset.fav || ""));
    btn.textContent = favored ? "❤️" : "♡";
    btn.classList.toggle("active", favored);
    btn.title = favored ? "取消收藏" : "收藏";
  });
}

function renderHero() {
  const cards = state.frontend.home.cards || {};
  $("heroKpis").innerHTML = [
    ["景点总量", cards.poi_total],
    ["覆盖城市", cards.city_total],
    ["覆盖省份", cards.province_total],
    ["高评分景点", cards.high_score_poi_total],
  ].map(([label, value]) => `<span><strong>${fmt(value)}</strong>${label}</span>`).join("");

  const rows = state.frontend.home.hot_poi_top10 || [];
  $("hotCarouselTrack").innerHTML = rows.slice(0, 6).map((row) => `<article class="carousel-card"><img src="${html(imageOf(row))}" alt="${html(row.poi_name)}"><div><span>${html(row.city_name)}</span><h3>${html(row.poi_name)}</h3><p>${html(row.short_feature || "华东热门景点")}</p></div></article>`).join("");
  $("hotCarouselDots").innerHTML = rows.slice(0, 6).map((_, index) => `<button data-dot="${index}"></button>`).join("");
  updateCarousel();
  clearInterval(window.__hotTimer);
  window.__hotTimer = setInterval(() => {
    state.carouselIndex = (state.carouselIndex + 1) % Math.max(1, Math.min(rows.length, 6));
    updateCarousel();
  }, 3200);
}

function updateCarousel() {
  const track = $("hotCarouselTrack");
  if (track) track.style.transform = `translateX(-${state.carouselIndex * 100}%)`;
  document.querySelectorAll("[data-dot]").forEach((dot) => dot.classList.toggle("active", Number(dot.dataset.dot) === state.carouselIndex));
}

function renderHome() {
  renderHomeHeatMap();
  setPie("homePriceChart", state.frontend.home.price_distribution || [], "price_level", "poi_count");
  const tags = (state.frontend.home.tag_top20 || []).slice(0, 10);
  setBar("homeTagChart", tags.map((x) => x.tag_name), tags.map((x) => x.poi_count), true, [palette.green, palette.teal]);
  const distanceRows = state.frontend.home.distance_distribution || [];
  setDistanceLevelChart("homeDistanceChart", distanceRows, "distance_level", "poi_count");
  const scoreRows = state.frontend.home.comment_score_distribution || [];
  setBar("homeCommentScoreChart", scoreRows.map((x) => x.score_band), scoreRows.map((x) => x.poi_count), false, [palette.green, palette.teal]);
}

function screenTargetCity() {
  const rows = state.flow?.forecast?.city_7day || [];
  if (!rows.length) return "";
  const bucket = new Map();
  rows.forEach((row) => {
    const key = row.city_name || "";
    const value = Number(row.forecast_flow || 0);
    bucket.set(key, Math.max(bucket.get(key) || 0, value));
  });
  return [...bucket.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || rows[0].city_name || "";
}

function renderScreenNews() {
  const box = $("screenNewsBoard");
  const status = $("screenNewsStatus");
  if (!box || !status) return;
  const rows = state.homeNews || [];
  status.textContent = rows.length ? `同步 ${formatNewsTime(state.homeNewsUpdatedAt)}` : "当前没有可展示公告";
  box.innerHTML = rows.length ? rows.slice(0, 6).map((row) => `
    <a class="screen-news-item" href="${html(row.link || "#")}" target="_blank" rel="noreferrer">
      <strong>${html(row.title || "-")}</strong>
      <p>${html(row.summary || "点击查看完整内容")}</p>
      <small>${html(row.source || "实时新闻")}</small>
      <time>${html(formatNewsTime(row.published_at))}</time>
    </a>
  `).join("") : `<div class="screen-empty">暂无旅游公告</div>`;
}

function renderScreenHeatMap() {
  const chart = state.charts.screenHeatMapChart;
  if (!chart) return;
  const rows = state.frontend?.home?.heatmap_points || [];
  if (!rows.length) {
    chart.setOption({
      ...baseChart(),
      title: { text: "暂无城市景点分布数据", left: "center", top: "middle", textStyle: { color: "#6b8371", fontSize: 18 } },
      xAxis: { show: false, type: "value" },
      yAxis: { show: false, type: "value" },
      series: [],
    }, true);
    return;
  }
  chart.setOption({
    ...baseChart(),
    tooltip: { formatter: (p) => `${p.data.name}<br>景点数量：${fmt(p.data.value[2])}<br>平均热度：${dec(p.data.heat, 1)}<br>平均评分：${dec(p.data.score, 1)}` },
    grid: { left: 48, right: 28, top: 18, bottom: 42 },
    xAxis: { type: "value", name: "经度", min: 113, max: 123, splitLine: { lineStyle: { color: "rgba(69,108,84,.08)" } } },
    yAxis: { type: "value", name: "纬度", min: 23, max: 38, splitLine: { lineStyle: { color: "rgba(69,108,84,.08)" } } },
    visualMap: { min: 0, max: Math.max(...rows.map((x) => Number(x.value || 0)), 1), right: 10, top: 12, calculable: true, inRange: { color: ["#e6f4d8", "#97c26c", "#418d68"] } },
    series: [{
      name: "景点分布",
      type: "effectScatter",
      coordinateSystem: "cartesian2d",
      data: rows.map((row) => ({ name: row.name, value: [row.lng, row.lat, row.value], heat: row.heat, score: row.score })),
      symbolSize: (value) => Math.max(10, Math.min(50, Math.sqrt(Number(value[2] || 0)) * 2.6)),
      rippleEffect: { brushType: "stroke", scale: 2.8 },
      itemStyle: { shadowBlur: 12, shadowColor: "rgba(65,141,104,.22)", color: "#4e996f" },
      label: { show: true, formatter: "{b}", position: "right", color: "#456c54", fontSize: 11 },
    }],
  });
}

function renderScreenFlow() {
  const rows = state.flow?.forecast?.city_7day || [];
  const cityName = screenTargetCity();
  const cityRows = rows.filter((row) => row.city_name === cityName).sort((a, b) => String(a.forecast_date).localeCompare(String(b.forecast_date)));
  $("screenFlowTitle").textContent = cityName ? `${cityName}未来7天客流` : "重点城市未来7天客流";
  setLine("screenFlowTrendChart", cityRows.map((x) => x.forecast_date), cityRows.map((x) => x.forecast_flow), palette.teal);
}

function renderScreenRanking() {
  const rows = (state.frontend?.detail_rankings?.hot_top20 || []).slice().sort((a, b) => Number(b.heat_score || 0) - Number(a.heat_score || 0)).slice(0, 10);
  setBar("screenRankingChart", rows.map((x) => x.poi_name), rows.map((x) => Number(x.heat_score || 0)), true, [palette.orange, palette.red]);
}

function renderScreenInsight() {
  const chartId = "screenInsightChart";
  if (state.role === "operator" && state.portrait?.preferences?.length) {
    const rows = state.portrait.preferences.slice(0, 8);
    $("screenInsightTitle").textContent = "游客偏好主题";
    $("screenInsightSub").textContent = "运营视角下的用户兴趣分布";
    setBar(chartId, rows.map((x) => x.preference_tag), rows.map((x) => x.user_count), true, [palette.green, palette.teal]);
    return;
  }
  const rows = (state.frontend?.home?.tag_top20 || []).slice(0, 8);
  $("screenInsightTitle").textContent = "热门主题分布";
  $("screenInsightSub").textContent = "游客视角下的华东热门主题";
  setBar(chartId, rows.map((x) => x.tag_name), rows.map((x) => x.poi_count), true, [palette.green, palette.teal]);
}

function renderScreenAlerts() {
  const rows = (state.flow?.forecast?.future_7day || [])
    .slice()
    .sort((a, b) => Number(b.forecast_flow || 0) - Number(a.forecast_flow || 0))
    .slice(0, 8);
  $("screenAlertBody").innerHTML = rows.length
    ? rows.map((row) => `<tr><td>${html(row.city_name || "-")}</td><td>${html(row.poi_name || "-")}</td><td>${html(row.forecast_date || "-")}</td><td>${fmt(row.forecast_flow)}</td></tr>`).join("")
    : `<tr><td colspan="4">暂无高峰预警数据</td></tr>`;
}

function renderBigScreen() {
  if (!$("dashboardPanel")) return;
  if (!state.frontend || !state.flow) return;
  const cards = state.frontend.home.cards || {};
  const cityRows = state.flow?.forecast?.city_7day || [];
  const cityCount = new Set(cityRows.map((row) => row.city_name).filter(Boolean)).size;
  const maxFlow = Math.max(...cityRows.map((row) => Number(row.forecast_flow || 0)), 0);
  const topCity = screenTargetCity();
  const operatorInteraction = state.portrait?.interaction || {};
  if ($("screenRoleLabel")) {
    $("screenRoleLabel").textContent = state.role === "operator" ? "运营者" : "游客端";
  }
  $("screenKpis").innerHTML = [
    ["景点总量", cards.poi_total || 0],
    ["覆盖城市", cards.city_total || 0],
    ["预测城市：", cityCount],
    ["最高预测客流", fmt(maxFlow)],
    [state.role === "operator" ? "评论总数" : "热门城市", state.role === "operator" ? fmt(operatorInteraction.comment_count || 0) : (topCity || "-")],
    [state.role === "operator" ? "评论用户：" : "新闻公告", state.role === "operator" ? fmt(operatorInteraction.comment_user_count || 0) : fmt((state.homeNews || []).length)],
  ].map(([label, value]) => `<span><strong>${html(String(value))}</strong>${html(label)}</span>`).join("");
  renderScreenHeatMap();
  renderScreenFlow();
  renderScreenRanking();
  renderScreenInsight();
  renderScreenNews();
  renderScreenAlerts();
}

function formatNewsTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

async function loadHomeNews() {
  const box = $("homeNewsBoard");
  const status = $("homeNewsStatus");
  if (!box || !status) return;
  status.textContent = "正在获取最新旅游新闻";
  try {
    const data = await fetchJson("/api/home-news");
    const rows = data.items || [];
    state.homeNews = rows;
    state.homeNewsUpdatedAt = data.updated_at || "";
    status.textContent = rows.length ? `已更新${formatNewsTime(data.updated_at)}，共抓取 ${rows.length} 条` : (data.message || "暂时没有抓到相关新闻");
    box.innerHTML = rows.length ? rows.map((row, index) => `
      <a class="news-item" href="${html(row.link || "#")}" target="_blank" rel="noreferrer">
        <span class="news-index">${index + 1}</span>
        <div class="news-copy">
          <strong>${html(row.title || "-")}</strong>
          <p>${html(row.summary || "点击查看完整新闻内容")}</p>
        </div>
        <div class="news-meta">
          <span>${html(row.source || "实时新闻")}</span>
          <time>${html(formatNewsTime(row.published_at))}</time>
        </div>
      </a>`).join("") : `<div class="news-empty">${html(data.message || "暂时没有抓到相关新闻")}</div>`;
    renderScreenNews();
  } catch (error) {
    state.homeNews = [];
    state.homeNewsUpdatedAt = "";
    status.textContent = "新闻暂时加载失败";
    box.innerHTML = `<div class="news-empty">${html(error.message || "新闻暂时加载失败")}</div>`;
    renderScreenNews();
  }
}

function renderHomeHeatMap() {
  const rows = state.frontend.home.heatmap_points || [];
  const chart = state.charts.homeHeatMapChart;
  if (!chart) return;
  if (!rows.length) {
    chart.setOption({
      ...baseChart(),
      title: { text: "暂无城市景点分布数据", left: "center", top: "middle", textStyle: { color: "#6b8371", fontSize: 18 } },
      xAxis: { show: false, type: "value" },
      yAxis: { show: false, type: "value" },
      series: [],
    }, true);
    return;
  }
  chart.setOption({
    ...baseChart(),
    tooltip: { formatter: (p) => `${p.data.name}<br>景点数量：${fmt(p.data.value[2])}<br>平均热度：${dec(p.data.heat, 1)}<br>平均评分：${dec(p.data.score, 1)}` },
    grid: { left: 66, right: 72, top: 22, bottom: 62, containLabel: true },
    xAxis: {
      type: "value",
      name: "经度",
      nameLocation: "end",
      nameGap: 18,
      nameTextStyle: { color: "#56736c", fontWeight: 700, align: "right", padding: [12, 0, 0, 0] },
      min: 113,
      max: 123,
      splitLine: { lineStyle: { color: "rgba(69,108,84,.1)" } },
    },
    yAxis: {
      type: "value",
      name: "纬度",
      nameLocation: "end",
      nameGap: 18,
      nameTextStyle: { color: "#56736c", fontWeight: 700, padding: [0, 0, 6, 0] },
      min: 23,
      max: 38,
      splitLine: { lineStyle: { color: "rgba(69,108,84,.1)" } },
    },
    visualMap: { min: 0, max: Math.max(...rows.map((x) => x.value), 1), right: 10, top: 10, calculable: true, inRange: { color: ["#f4d6b7", "#d89a45", "#c65d3b"] } },
    series: [{
      name: "景点分布",
      type: "effectScatter",
      coordinateSystem: "cartesian2d",
      data: rows.map((row) => ({ name: row.name, value: [row.lng, row.lat, row.value], heat: row.heat, score: row.score })),
      symbolSize: (value) => Math.max(10, Math.min(48, Math.sqrt(value[2]) * 2.8)),
      rippleEffect: { brushType: "stroke", scale: 2.5 },
      label: { show: true, formatter: "{b}", position: "right", color: "#4c382c", fontSize: 11 },
      itemStyle: { shadowBlur: 12, shadowColor: "rgba(198,93,59,.28)" },
    }],
  }, true);
}

function startClockAndLocation() {
  const update = () => {
    const text = new Date().toLocaleString("zh-CN", { hour12: false });
    $("topClock").textContent = text;
    $("homeClock").textContent = text;
    if ($("screenClock")) $("screenClock").textContent = text;
    if ($("commentNow")) $("commentNow").textContent = `当前时间：{text}`;
  };
  update();
  setInterval(update, 1000);
  if (!navigator.geolocation) {
    $("homeLocation").textContent = "默认上海";
    if ($("screenLocation")) $("screenLocation").textContent = "默认上海";
    loadWeather(31.2304, 121.4737);
    return;
  }
  navigator.geolocation.getCurrentPosition(async (pos) => {
    const { latitude, longitude } = pos.coords;
    $("homeLocation").textContent = `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`;
    if ($("screenLocation")) $("screenLocation").textContent = `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`;
    loadWeather(latitude, longitude);
  }, () => {
    $("homeLocation").textContent = "默认上海";
    if ($("screenLocation")) $("screenLocation").textContent = "默认上海";
    loadWeather(31.2304, 121.4737);
  }, { timeout: 8000 });
}

async function loadWeather(lat, lon) {
  try {
    const data = await fetchJson(`/api/weather/current?lat=${lat}&lon=${lon}`);
    $("homeLocation").textContent = data.location || `${Number(lat).toFixed(3)}, ${Number(lon).toFixed(3)}`;
    if ($("screenLocation")) $("screenLocation").textContent = data.location || `${Number(lat).toFixed(3)}, ${Number(lon).toFixed(3)}`;
    if (data.temperature === null || data.temperature === undefined) {
      $("homeWeather").textContent = "天气暂不可用";
      if ($("screenWeather")) $("screenWeather").textContent = "天气暂不可用";
    } else {
      const weatherText = data.weather ? `${data.weather} · ` : "";
      const windText = windSummary(data);
      const weatherLine = `${weatherText}${dec(data.temperature, 1)}℃${windText ? ` · ${windText}` : ""}`;
      $("homeWeather").textContent = weatherLine;
      if ($("screenWeather")) $("screenWeather").textContent = weatherLine;
    }
  } catch {
    $("homeWeather").textContent = "天气暂不可用";
    if ($("screenWeather")) $("screenWeather").textContent = "天气暂不可用";
  }
}

function buildRegionSelectors() {
  const region = state.frontend.region_dashboard;
  state.provinceName = region.province_summary[0]?.province || "";
  state.cityName = region.city_summary[0]?.city_name || "";
  $("provinceSelector").innerHTML = region.province_summary.map((row) => `<option value="${html(row.province)}">${html(row.province)}</option>`).join("");
  $("citySelector").innerHTML = region.city_summary.map((row) => `<option value="${html(row.city_name)}">${html(row.city_name)}</option>`).join("");
  $("provinceSelector").addEventListener("change", () => { state.provinceName = $("provinceSelector").value; renderRegion(); });
  $("citySelector").addEventListener("change", () => { state.cityName = $("citySelector").value; renderRegion(); });
  document.querySelectorAll("[data-region-mode]").forEach((btn) => btn.addEventListener("click", () => {
    state.regionMode = btn.dataset.regionMode;
    document.querySelectorAll("[data-region-mode]").forEach((b) => b.classList.toggle("active", b === btn));
    renderRegion();
  }));
}

function provinceTagRows(province) {
  const region = state.frontend.region_dashboard;
  const cities = new Set(region.city_summary.filter((x) => x.province === province).map((x) => x.city_name));
  const count = {};
  region.city_tag_summary.filter((x) => cities.has(x.city_name)).forEach((row) => { count[row.tag_name] = (count[row.tag_name] || 0) + Number(row.poi_count || 0); });
  return Object.entries(count).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([tag_name, poi_count]) => ({ tag_name, poi_count }));
}

function regionMaxima(isProvince) {
  const rows = isProvince ? state.frontend.region_dashboard.province_summary : state.frontend.region_dashboard.city_summary;
  return {
    poi_count: Math.max(...rows.map((x) => Number(x.poi_count || 0)), 1),
    avg_heat: Math.max(...rows.map((x) => Number(x.avg_heat || 0)), 1),
    avg_score: Math.max(...rows.map((x) => Number(x.avg_score || 0)), 1),
    comment_total: Math.max(...rows.map((x) => Number(x.comment_total || 0)), 1),
  };
}

function normalizedRegionRows(item, isProvince) {
  const max = regionMaxima(isProvince);
  const highRatio = Number(item.high_score_ratio || (Number(item.high_score_poi_count || 0) / Math.max(Number(item.poi_count || 0), 1)));
  return [
    { name: "景点规模", value: Math.min(100, Number(item.poi_count || 0) / max.poi_count * 100) },
    { name: "免费占比", value: freeRatioOf(item) * 100 },
    { name: "平均热度", value: Math.min(100, Number(item.avg_heat || 0) / max.avg_heat * 100) },
    { name: "平均评分", value: Math.min(100, Number(item.avg_score || 0) / max.avg_score * 100) },
    { name: "高评占比", value: highRatio * 100 },
    { name: "评论规模", value: Math.min(100, Number(item.comment_total || 0) / max.comment_total * 100) },
  ];
}

function setRadarChart(id, rows) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.setOption({
    ...baseChart(),
    tooltip: {},
    radar: {
      radius: "68%",
      indicator: rows.map((x) => ({ name: x.name, max: 100 })),
      axisName: { color: "#56736c", fontWeight: 700 },
      splitLine: { lineStyle: { color: "rgba(54,112,103,.16)" } },
      splitArea: { areaStyle: { color: ["rgba(107,179,162,.05)", "rgba(242,177,92,.06)"] } },
      axisLine: { lineStyle: { color: "rgba(54,112,103,.18)" } },
    },
    series: [{
      type: "radar",
      data: [{
        value: rows.map((x) => Number(x.value || 0)),
        areaStyle: { color: "rgba(84, 159, 142, .24)" },
        lineStyle: { color: palette.teal, width: 3 },
        itemStyle: { color: palette.teal },
      }],
    }],
  });
}

function renderRegion() {
  const region = state.frontend.region_dashboard;
  const isProvince = state.regionMode === "province";
  $("provinceSelectorWrap").classList.toggle("hidden", !isProvince);
  $("citySelectorWrap").classList.toggle("hidden", isProvince);
  $("regionOverviewTitle").textContent = isProvince ? "当前省份景点概况" : "当前城市景点概况";
  $("regionTagTitle").textContent = isProvince ? "当前省份主题画像" : "当前城市主题画像";
  $("regionOverviewSub").textContent = isProvince ? "按省份聚合运营" : "按城市聚合运营";
  const current = isProvince ? region.province_summary.find((x) => x.province === state.provinceName) : region.city_summary.find((x) => x.city_name === state.cityName);
  const insight = current || {};
  $("regionInsightCards").innerHTML = [
    ["景点数量", insight.poi_count],
    [isProvince ? "覆盖城市" : "所属省份", isProvince ? insight.city_count : insight.province],
    ["平均热度", dec(insight.avg_heat, 1)],
    ["免费占比", pct(freeRatioOf(insight))],
  ].map(([label, value]) => `<article><strong>${value ?? "-"}</strong><span>${label}</span></article>`).join("");

  setRadarChart("regionRankChart", normalizedRegionRows(insight, isProvince));

  const tags = isProvince ? provinceTagRows(state.provinceName) : region.city_tag_summary.filter((x) => x.city_name === state.cityName).slice(0, 6);
  const max = Math.max(...tags.map((x) => Number(x.poi_count) || 1), 1);
  state.charts.cityTagRadarChart.setOption({ ...baseChart(), radar: { indicator: tags.map((x) => ({ name: x.tag_name, max })), axisName: { color: "#5b4a3d" } }, series: [{ type: "radar", data: [{ value: tags.map((x) => x.poi_count), areaStyle: { color: "rgba(198,93,59,.22)" }, lineStyle: { color: palette.red }, itemStyle: { color: palette.red } }] }] });

  const provinceCities = new Set(region.city_summary.filter((x) => x.province === state.provinceName).map((x) => x.city_name));
  const poiRows = isProvince
    ? (region.province_top_poi?.[state.provinceName] || region.city_top_poi.filter((x) => provinceCities.has(x.city_name)))
    : region.city_top_poi.filter((x) => x.city_name === state.cityName);
  const rankedRows = poiRows.slice().sort((a, b) => compositeScore(b) - compositeScore(a));
  $("cityTopPoiList").innerHTML = scenicCards(rankedRows, 8);
  bindCardActions($("cityTopPoiList"));
}

function buildFilterSelectors() {
  const options = state.frontend.filter_panel.options;
  const provinces = [...new Set((state.frontend.region_dashboard?.province_summary || []).map((x) => x.province).filter(Boolean))];
  $("filterProvinceSelector").innerHTML = ["全部省份", ...provinces].map((x) => `<option>${html(x)}</option>`).join("");
  $("filterCitySelector").innerHTML = ["全部城市", ...(options.city_options || []).slice(0, 80)].map((x) => `<option>${html(x)}</option>`).join("");
  $("filterPriceSelector").innerHTML = ["全部价格", ...(options.price_level_options || [])].map((x) => `<option>${html(x)}</option>`).join("");
  $("filterTagSelector").innerHTML = ["全部主题", ...(options.tag_options || []).slice(0, 40)].map((x) => `<option>${html(x)}</option>`).join("");
  rebuildFilterCitySelector();
  $("filterProvinceSelector").addEventListener("change", () => {
    rebuildFilterCitySelector(true);
    updateFilterSearchSuggestions();
    renderFilter();
  });
  ["filterCitySelector", "filterPriceSelector", "filterTagSelector"].forEach((id) => $(id).addEventListener("change", () => {
    updateFilterSearchSuggestions();
    renderFilter();
  }));
  $("filterSearchInput").addEventListener("input", () => {
    updateFilterSearchSuggestions();
    renderFilter();
  });
  $("filterSearchInput").addEventListener("change", renderFilter);
  $("filterResetButton")?.addEventListener("click", () => {
    $("filterProvinceSelector").value = "全部省份";
    rebuildFilterCitySelector();
    $("filterPriceSelector").value = "全部价格";
    $("filterTagSelector").value = "全部主题";
    $("filterSearchInput").value = "";
    updateFilterSearchSuggestions();
    renderFilter();
  });
  updateFilterSearchSuggestions();
}

function priceMatch(row, group) {
  if (group === "全部价格") return true;
  const price = Number(row.price || 0);
  if (group.includes("免费")) return price === 0;
  if (group.includes("0-100")) return price > 0 && price <= 100;
  if (group.includes("100-250")) return price > 100 && price <= 250;
  return price > 250;
}

function filteredPois() {
  const province = $("filterProvinceSelector").value || "全部省份";
  const city = $("filterCitySelector").value || "全部城市";
  const price = $("filterPriceSelector").value || "全部价格";
  const tag = $("filterTagSelector").value || "全部主题";
  const keyword = String($("filterSearchInput")?.value || "").trim().toLowerCase();
  return (state.frontend.filter_panel.sample_poi || [])
    .filter((row) => (province === "全部省份" || row.province === province)
      && (city === "全部城市" || row.city_name === city)
      && priceMatch(row, price)
      && (tag === "全部主题" || String(row.tag_text || "").includes(tag))
      && (!keyword || searchTextOf(row).includes(keyword)))
    .sort((a, b) => compositeScore(b) - compositeScore(a));
}

function filterScoreBins(rows) {
  const bins = [
    { label: "4.8-5.0", min: 4.8, max: 5.01 },
    { label: "4.5-4.7", min: 4.5, max: 4.8 },
    { label: "4.0-4.4", min: 4.0, max: 4.5 },
    { label: "3.5-3.9", min: 3.5, max: 4.0 },
    { label: "3.0以下", min: -1, max: 3.5 },
  ];
  return bins.map((bin) => ({
    score_band: bin.label,
    poi_count: rows.filter((row) => {
      const score = Number(row.comment_score || 0);
      return score >= bin.min && score < bin.max;
    }).length,
  }));
}

function filterPriceScoreRows(rows) {
  return rows
    .filter((row) => Number.isFinite(Number(row.comment_score || 0)))
    .map((row) => ({
      ...row,
      priceValue: Math.max(0, Number(row.price || 0)),
      scoreValue: Math.max(0, Number(row.comment_score || 0)),
      heatValue: Math.max(1, Number(row.heat_score || 0)),
    }))
    .sort((a, b) => Number(b.comment_count || 0) - Number(a.comment_count || 0))
    .slice(0, 80);
}

function filterPriceBandRows(rows) {
  const bands = [
    { label: "免费", min: -0.01, max: 0.01 },
    { label: "0-100", min: 0.01, max: 100.01 },
    { label: "100-250", min: 100.01, max: 250.01 },
    { label: "250+", min: 250.01, max: Number.POSITIVE_INFINITY },
  ];
  return bands.map((band) => {
    const matched = rows.filter((row) => {
      const price = Number(row.price || 0);
      return price > band.min && price <= band.max;
    });
    const scores = matched
      .map((row) => Number(row.comment_score || 0))
      .filter((value) => Number.isFinite(value) && value > 0);
    const heatValues = matched
      .map((row) => Number(row.heat_score || 0))
      .filter((value) => Number.isFinite(value) && value > 0);
    const sortedScores = scores.slice().sort((a, b) => a - b);
    const medianScore = sortedScores.length
      ? (sortedScores.length % 2
        ? sortedScores[(sortedScores.length - 1) / 2]
        : (sortedScores[sortedScores.length / 2 - 1] + sortedScores[sortedScores.length / 2]) / 2)
      : 0;
    return {
      label: band.label,
      poiCount: matched.length,
      minScore: scores.length ? Math.min(...scores) : 0,
      maxScore: scores.length ? Math.max(...scores) : 0,
      medianScore,
      avgHeat: heatValues.length ? heatValues.reduce((sum, value) => sum + value, 0) / heatValues.length : 0,
    };
  });
}

function topTags(rows, limit = 8) {
  const tagCount = {};
  rows.slice(0, 220).forEach((row) => {
    String(row.tag_text || "")
      .split(/[|,，]/)
      .map((item) => item.trim())
      .filter(Boolean)
      .forEach((item) => {
        tagCount[item] = (tagCount[item] || 0) + 1;
      });
  });
  return Object.entries(tagCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([tag, count]) => ({ tag, count }));
}

function setFilterPriceScoreChart(id, rows) {
  const chart = state.charts[id];
  if (!chart) return;
  if (!rows.length) {
    setEmptyChart(id, "暂无匹配结果，价格与评分关系无法展示");
    return;
  }
  const validRows = rows.filter((row) => row.poiCount > 0);
  if (!validRows.length) {
    setEmptyChart(id, "暂无匹配结果，价格与评分关系无法展示");
    return;
  }
  const minScore = Math.max(3, Math.floor((Math.min(...validRows.map((row) => row.minScore || row.medianScore)) - 0.12) * 10) / 10);
  const maxScore = Math.min(5, Math.ceil((Math.max(...validRows.map((row) => row.maxScore || row.medianScore)) + 0.08) * 10) / 10);
  chart.setOption({
    ...baseChart(),
    tooltip: {
      formatter(params) {
        const row = rows[params.dataIndex] || {};
        return `${html(row.label || "-")}<br>景点数：${fmt(row.poiCount || 0)}<br>评分中位数：${dec(row.medianScore || 0, 2)}<br>评分范围：${dec(row.minScore || 0, 1)} - ${dec(row.maxScore || 0, 1)}<br>平均热度：${dec(row.avgHeat || 0, 1)}`;
      },
    },
    grid: { left: 52, right: 18, top: 24, bottom: 40 },
    xAxis: {
      type: "category",
      data: rows.map((row) => row.label),
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    yAxis: {
      type: "value",
      name: "评分",
      min: minScore,
      max: maxScore,
      interval: 0.2,
      axisLabel: { formatter: (value) => Number(value).toFixed(1) },
      splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
    },
    series: [
      {
        type: "bar",
        barWidth: 28,
        data: rows.map((row) => ({
          value: row.maxScore > row.minScore ? row.maxScore - row.minScore : 0.04,
          itemStyle: {
            color: "rgba(119, 176, 136, 0.22)",
            borderRadius: 10,
          },
        })),
        stack: "score-band",
        silent: true,
      },
      {
        type: "bar",
        barWidth: 28,
        data: rows.map((row) => ({
          value: row.minScore > 0 ? row.minScore - minScore : 0,
          itemStyle: { color: "rgba(0,0,0,0)" },
        })),
        stack: "score-band",
        silent: true,
      },
      {
        type: "line",
        data: rows.map((row) => Number(row.medianScore || 0)),
        symbol: "circle",
        symbolSize: 12,
        smooth: 0.2,
        lineStyle: { width: 3, color: palette.green },
        itemStyle: {
          color: "#ffffff",
          borderColor: palette.green,
          borderWidth: 3,
          shadowBlur: 8,
          shadowColor: "rgba(95,154,99,.18)",
        },
        label: {
          show: true,
          position: "top",
          color: "#557765",
          fontWeight: 700,
          formatter: (params) => dec(params.value, 2),
        },
        z: 5,
      },
    ],
  });
}

function filterSummary(rows) {
  const total = rows.length;
  const avgScore = total ? rows.reduce((sum, row) => sum + Number(row.comment_score || 0), 0) / total : 0;
  const avgHeat = total ? rows.reduce((sum, row) => sum + Number(row.heat_score || 0), 0) / total : 0;
  const freeCount = rows.filter((row) => Number(row.price || 0) <= 0).length;
  const cityCount = new Set(rows.map((row) => row.city_name).filter(Boolean)).size;
  return [
    { label: "匹配景点", value: fmt(total), extra: cityCount ? `覆盖 ${cityCount} 个城市` : "暂无城市数据" },
    { label: "平均评分", value: total ? dec(avgScore, 2) : "-", extra: "按当前筛选结果统计" },
    { label: "平均热度", value: total ? dec(avgHeat, 1) : "-", extra: "热度越高，讨论越集中" },
    { label: "免费占比", value: total ? pct(freeCount / total) : "-", extra: "当前结果中的免费景点" },
  ];
}

function setEmptyChart(id, message) {
  const chart = state.charts[id];
  if (!chart) return;
  chart.clear();
  chart.setOption({
    ...baseChart(),
    graphic: [{
      type: "text",
      left: "center",
      top: "middle",
      style: {
        text: message,
        fill: "#6a836f",
        fontSize: 16,
        fontWeight: 600,
        textAlign: "center",
      },
    }],
  });
}

function renderFilter() {
  const rows = filteredPois();
  const province = $("filterProvinceSelector").value || "全部省份";
  const city = $("filterCitySelector").value || "全部城市";
  const price = $("filterPriceSelector").value || "全部价格";
  const tag = $("filterTagSelector").value || "全部主题";
  const keyword = String($("filterSearchInput")?.value || "").trim();
  $("filterMetricStrip").innerHTML = filterSummary(rows).map((item) => `<span><strong>${html(item.value)}</strong>${html(item.label)}<small>${html(item.extra)}</small></span>`).join("");
  const tagCount = {};
  rows.slice(0, 220).forEach((row) => String(row.tag_text || "").split(/[|,，]/).forEach((tag) => tag && (tagCount[tag] = (tagCount[tag] || 0) + 1)));
  const tagRows = Object.entries(tagCount).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([tag, count]) => ({ tag, count }));
  const scoreRows = filterScoreBins(rows);
  const priceScoreRows = filterPriceScoreRows(rows);
  if (!rows.length) {
    $("filterResultMeta").textContent = "当前条件下没有匹配到景点。可以先放宽城市、主题或关键词，再看分布。";
    setEmptyChart("filterScoreChart", "暂无匹配结果，价格与评分关系无法展示");
    setEmptyChart("filterTagChart", "暂无匹配结果，主题分布无法展示");
    $("filterInsightCard").innerHTML = `
      <h3>筛选洞察</h3>
      <p>当前条件较严，建议先保留省份或城市，再逐步增加主题和关键词约束。</p>
      <div class="insight-tags">
        <span>省份：${html(province)}</span>
        <span>城市：${html(city)}</span>
        <span>价格：${html(price)}</span>
        <span>主题：${html(tag)}</span>
        <span>关键词：${html(keyword || "无")}</span>
      </div>
    `;
    $("filterPoiList").innerHTML = `<div class="plan-empty">没有可展示的景点结果</div>`;
    return;
  }
  setScatter("filterScoreChart", priceScoreRows, (row) => row.priceValue, (row) => row.scoreValue, (row) => row.heatValue * 180, "价格", "评分", palette.green);
  setBar("filterTagChart", tagRows.map((x) => x.tag), tagRows.map((x) => x.count), true, [palette.orange, palette.red]);
  $("filterResultMeta").textContent = `当前匹配 ${fmt(rows.length)} 个景点，默认展示热度最高的 8 个结果。`;
  $("filterInsightCard").innerHTML = `
    <h3>筛选洞察</h3>
    <p>评分主要集中在 ${scoreRows.filter((x) => x.poi_count).map((x) => x.score_band).join("、") || "暂无"}，主题偏好以 ${tagRows[0]?.tag || "暂无"} 为主。</p>
    <div class="insight-tags">
      <span>当前城市：${html(city)}</span>
      <span>价格条件：${html(price)}</span>
      <span>主题条件：${html(tag)}</span>
      <span>关键词：${html(keyword || "无")}</span>
    </div>
    <div class="insight-lead">
      <strong>推荐优先查看：</strong>
      <span>${html(rows[0]?.poi_name || "暂无")}</span>
    </div>
  `;
  $("filterPoiList").innerHTML = scenicCards(rows.slice(0, 8), 8);
  bindCardActions($("filterPoiList"));
}

function buildRankTabs() {
  $("detailRankTabs").innerHTML = Object.entries(rankMap).map(([key, label]) => `<button class="chip ${key === state.activeRank ? "active" : ""}" data-rank="${key}">${label}</button>`).join("");
  document.querySelectorAll("[data-rank]").forEach((btn) => btn.addEventListener("click", () => { state.activeRank = btn.dataset.rank; buildRankTabs(); renderRanking(); }));
}

function renderRanking() {
  const rows = (state.frontend.detail_rankings[state.activeRank] || []).slice().sort((a, b) => {
    if (state.activeRank === "value_top20") {
      const scoreDiff = Number(b.ranking_score || 0) - Number(a.ranking_score || 0);
      if (scoreDiff !== 0) return scoreDiff;
    }
    const heatDiff = Number(b.heat_score || 0) - Number(a.heat_score || 0);
    if (heatDiff !== 0) return heatDiff;
    const commentDiff = Number(b.comment_count || 0) - Number(a.comment_count || 0);
    if (commentDiff !== 0) return commentDiff;
    return Number(b.comment_score || 0) - Number(a.comment_score || 0);
  });
  const topHeatRows = rows.slice(0, 8);
  setBarCompact("detailRankChart", topHeatRows.map((x) => x.poi_name), topHeatRows.map((x) => x.heat_score || 0), [palette.blue, palette.teal]);
  setRankingScatter("detailScoreChart", rows);
  $("detailRankList").innerHTML = scenicCards(rows.slice(0, 8), 8);
  bindCardActions($("detailRankList"));
}

function buildRecommendSelector() {
  if (!$("recommendAlgorithmSelector")) {
    const fixedPill = document.querySelector(".recommend-fixed-pill");
    if (fixedPill) {
      fixedPill.outerHTML = '<select id="recommendAlgorithmSelector"></select>';
    }
  }
  const algorithms = state.frontend.recommendation.algorithms || [];
  const modes = state.frontend.recommendation.modes || [];
  const provinces = locationProvinces();
  if (!algorithms.some((x) => x.key === state.recommendAlgorithm)) state.recommendAlgorithm = algorithms[0]?.key || "als";
  if (!modes.some((x) => x.key === state.recommendMode)) state.recommendMode = modes[0]?.key || "balanced";
  if (!state.recommendProvince) state.recommendProvince = provinces[0] || "";
  if (!state.recommendCity && state.recommendProvince) state.recommendCity = locationCities(state.recommendProvince)[0]?.city_name || "";
  if (!state.recommendPoi && state.recommendProvince && state.recommendCity) state.recommendPoi = locationPois(state.recommendProvince, state.recommendCity)[0]?.poi_name || "";
  $("recommendProvinceInput").value = state.recommendProvince;
  $("recommendCityInput").value = state.recommendCity;
  $("recommendPoiInput").value = state.recommendPoi;
  $("recommendAlgorithmSelector").innerHTML = algorithms.map((x) => `<option value="${x.key}" ${x.key === state.recommendAlgorithm ? "selected" : ""}>${html(x.name)}</option>`).join("");
  $("recommendProvinceOptions").innerHTML = provinces.map((x) => `<option value="${html(x)}"></option>`).join("");
  updateRecommendCityOptions();
  updateRecommendPoiOptions();
  $("recommendModeSelector").innerHTML = modes.map((x) => `<option value="${x.key}" ${x.key === state.recommendMode ? "selected" : ""}>${html(x.name)}</option>`).join("");
  $("recommendAlgorithmSelector").addEventListener("change", () => {
    state.recommendAlgorithm = $("recommendAlgorithmSelector").value;
    if (state.recommendAlgorithm === "als") {
      state.recommendMode = "balanced";
      state.recommendProvince = "";
      state.recommendCity = "";
      state.recommendPoi = "";
      $("recommendModeSelector").value = "balanced";
      $("recommendProvinceInput").value = "";
      $("recommendCityInput").value = "";
      $("recommendPoiInput").value = "";
    }
    renderAlgorithmNote();
    updateRecommendInputsState();
  });
  $("recommendProvinceInput").addEventListener("input", () => {
    const value = $("recommendProvinceInput").value.trim();
    const matched = locationProvinces().find((item) => item === value);
    state.recommendProvince = matched || value;
    state.recommendCity = "";
    state.recommendPoi = "";
    $("recommendCityInput").value = "";
    $("recommendPoiInput").value = "";
    updateRecommendCityOptions();
    updateRecommendPoiOptions();
    updateRecommendInputsState();
    renderAlgorithmNote();
  });
  $("recommendCityInput").addEventListener("input", () => {
    const value = $("recommendCityInput").value.trim();
    const matched = fuzzyPick(locationCities(state.recommendProvince), value, ["city_name", "province"])[0];
    state.recommendCity = matched?.city_name || value;
    state.recommendPoi = "";
    $("recommendPoiInput").value = "";
    updateRecommendPoiOptions();
    updateRecommendInputsState();
    renderAlgorithmNote();
  });
  $("recommendPoiInput").addEventListener("input", () => {
    state.recommendPoi = $("recommendPoiInput").value.trim();
    updateRecommendPoiOptions();
    syncRecommendStepbar();
  });
  $("recommendModeSelector").addEventListener("change", () => {
    state.recommendMode = $("recommendModeSelector").value;
    renderAlgorithmNote();
  });
  $("recommendTrigger").addEventListener("click", loadRecommendations);
  renderAlgorithmNote();
}

function renderAlgorithmNote(algorithm = null) {
  const algorithms = state.frontend.recommendation.algorithms || [];
  const modes = state.frontend.recommendation.modes || [];
  const currentAlgorithm = state.recommendAlgorithm || "als";
  const item = algorithm || algorithms.find((x) => x.key === currentAlgorithm) || { key: "als", name: "ALS 协同过滤推荐", principle: "把收藏按 4 分、评论按真实评分合并成用户-景点评分矩阵，再用交替最小二乘分解出个性化推荐结果。" };
  const mode = modes.find((x) => x.key === state.recommendMode) || modes[0];
  const modeText = mode ? `<p><b>${html(mode.name)}</b>：${html(mode.description || "")}</p>` : "";
  const pathText = [state.recommendProvince, state.recommendCity, state.recommendPoi].filter(Boolean).join(" / ");
  const historyText = item.key === "als"
    ? (state.currentUser ? `<p>当前账号：${html(state.currentUser.nickname || state.currentUser.username || "")}，会优先使用你的收藏和评论历史。</p>` : "<p>登录游客账号后，系统会结合你的收藏和评论历史生成推荐。</p>")
    : "<p>混合推荐会综合地理邻近、内容相似、规则偏好和景点品质，给出更可解释的推荐结果。</p>";
  const flowHint = item.key === "als"
    ? "<p>ALS 模式下无需继续选择省份、城市、景点和模式，点击生成即可直接展示推荐。</p>"
    : "<p>混合推荐模式下请继续完成省份 -> 城市 -> 景点 -> 模式，再生成推荐。</p>";
  $("recommendAlgorithmNote").innerHTML = item ? `<strong>${html(item.name)}</strong><p>${html(item.principle)}</p>${historyText}${flowHint}${item.key === "hybrid" && pathText ? `<p>当前选择：${html(pathText)}</p>` : ""}${item.key === "hybrid" ? modeText : ""}` : "";
}

async function loadRecommendations() {
  const button = $("recommendTrigger");
  const originalText = button?.textContent || "";
  if (button) {
    button.disabled = true;
    button.textContent = "生成中...";
  }
  state.recommendAlgorithm = $("recommendAlgorithmSelector")?.value || state.recommendAlgorithm || "als";
  $("recommendMeta").textContent = state.recommendAlgorithm === "als"
    ? "正在结合当前账号行为生成 ALS 推荐..."
    : "正在根据景点内容、距离与口碑规则生成混合推荐...";
  try {
    if (state.recommendAlgorithm === "als" && (!state.currentUser || state.currentUser.role !== "tourist")) {
      throw new Error("请先登录游客账号，再生成个性化推荐");
    }
    const params = new URLSearchParams({ algorithm: state.recommendAlgorithm, limit: "8" });
    if (state.currentUser?.id) params.set("user_id", String(state.currentUser.id || ""));
    if (state.recommendAlgorithm === "hybrid") {
      state.recommendMode = $("recommendModeSelector").value;
      state.recommendProvince = $("recommendProvinceInput").value.trim();
      state.recommendCity = $("recommendCityInput").value.trim();
      state.recommendPoi = $("recommendPoiInput").value.trim();
      if (!state.recommendProvince) {
        throw new Error("请先输入省份，再生成推荐");
      }
      const resolved = await resolveRecommendLocation();
      if (resolved) {
        state.recommendProvince = resolved.province || state.recommendProvince;
        state.recommendCity = resolved.city || state.recommendCity;
        state.recommendPoi = resolved.poi || state.recommendPoi;
        $("recommendProvinceInput").value = state.recommendProvince;
        $("recommendCityInput").value = state.recommendCity;
        $("recommendPoiInput").value = state.recommendPoi;
        updateRecommendCityOptions();
        updateRecommendPoiOptions();
        updateRecommendInputsState();
      }
      if (!state.recommendCity || !state.recommendPoi) {
        throw new Error("请先完成省份 -> 城市 -> 景点选择，再生成推荐");
      }
      params.set("mode", state.recommendMode);
      params.set("province", state.recommendProvince);
      params.set("city", state.recommendCity);
      params.set("poi_name", state.recommendPoi);
    }
    const data = await fetchJson(`/api/recommendations?${params.toString()}`);
    renderRecommend(data);
  } catch (error) {
    $("recommendMeta").textContent = error.message || "推荐生成失败，请调整景点后重试";
    $("recommendNote").innerHTML = `<div class="plan-empty">${html(error.message || "推荐生成失败，请调整景点后重试")}</div>`;
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
  }
}

function recommendScoreValue(row) {
  const raw = Number(row.recommend_score || row.final_score || row.heat_score || 0);
  return raw > 0 && raw <= 1 ? raw * 100 : raw;
}

function renderSubScoreChips(row) {
  const scores = row?.sub_scores || {};
  const labels = { content: "内容", geo: "距离", rule: "规则", behavior: "ALS", quality: "品质" };
  const chips = Object.entries(labels).map(([key, label]) => {
    const value = Number(scores[key] || 0);
    return `<span>${label} ${dec(value * 100, 0)}</span>`;
  });
  return `<div class="poi-meta">${chips.join("")}</div>`;
}

function renderRecommendSummaryItem(row) {
  const price = Number(row.price || 0) > 0 ? `¥${dec(row.price, 0)}` : "免费";
  const distance = Number(row.distance_km || 0) > 0 ? `${dec(row.distance_km, 2)}km` : (row.distance_level || "距离待补充");
  const tags = String(row.shared_tags || row.tag_text || "").split(/[、,，]/).map((item) => item.trim()).filter(Boolean).slice(0, 4);
  const tagText = tags.length ? `<p>匹配标签：${tags.map(html).join("、")}</p>` : "";
  return `
    <section class="recommend-detail-item">
      <h3>${html(row.poi_name || "-")}</h3>
      <p>${html(row.city_name || "-")} / ${html(row.region_name || "景区")} · ${html(distance)} · ${html(price)}</p>
      <p>${html(row.reason_text || row.short_feature || "基于当前景点生成推荐")}</p>
      <div class="poi-meta">
        <span>评分 ${dec(row.comment_score || 0)}</span>
        <span>热度 ${dec(row.heat_score || 0)}</span>
        <span>评论 ${fmt(row.comment_count || 0)}</span>
        <span>层级 ${html(row.distance_level || "-")}</span>
      </div>
      ${tagText}
      ${row.sub_scores ? renderSubScoreChips(row) : ""}
    </section>`;
}

function renderRecommend(data = null) {
  const rows = data?.recommendations || state.frontend.recommendation.cards || [];
  if (data?.algorithm) {
    state.recommendAlgorithm = data.algorithm.key || "als";
    state.recommendMode = data.mode?.key || state.recommendMode;
    if ($("recommendAlgorithmSelector")) $("recommendAlgorithmSelector").value = state.recommendAlgorithm;
    if ($("recommendModeSelector")) $("recommendModeSelector").value = state.recommendMode;
    renderAlgorithmNote(data.algorithm);
  }
  $("recommendMeta").textContent = data?.matched_name
    ? `当前结果：${data.matched_name}`
    : (state.recommendAlgorithm === "als" ? "点击生成即可直接展示 ALS 推荐结果" : "请先完成省份 -> 城市 -> 景点选择，再生成推荐");
  $("recommendNote").innerHTML = rows.slice(0, 3).length
    ? rows.slice(0, 3).map(renderRecommendSummaryItem).join("")
    : `<div class="plan-empty">当前还没有可展示的结果，请先完成地点选择。</div>`;
  setBar("recommendScoreChart", rows.slice(0, 8).map((x) => x.poi_name), rows.slice(0, 8).map(recommendScoreValue), true, [palette.green, palette.teal]);
  $("recommendCardGrid").innerHTML = scenicCards(rows, 8, { showDesc: false });
  bindCardActions($("recommendCardGrid"));
  updateRecommendInputsState();
}

function buildForecastSelector() {
  const rows = state.flow.forecast.city_7day || [];
  const cities = [...new Set(rows.map((x) => x.city_name))].sort();
  state.forecastCity = cities[0] || "";
  $("forecastCitySelector").innerHTML = cities.map((x) => `<option value="${html(x)}">${html(x)}</option>`).join("");
  $("forecastCitySelector").addEventListener("change", () => { state.forecastCity = $("forecastCitySelector").value; buildForecastDateSelector(); renderFlow(); });
  $("forecastDateSelector").addEventListener("change", renderFlow);
  buildForecastDateSelector();
}

function buildForecastDateSelector() {
  const dates = [...new Set((state.flow.forecast.city_7day || []).filter((x) => x.city_name === state.forecastCity).map((x) => x.forecast_date))].sort();
  $("forecastDateSelector").innerHTML = dates.map((x) => `<option value="${html(x)}">${html(x)}</option>`).join("");
}

function displayTemperature(row) {
  const value = Number(row.avg_temperature || 0);
  const month = String(row.forecast_date || "").slice(5, 7);
  if (month === "01" && value > 15) return value - 11.5;
  if (month === "02" && value > 17) return value - 8;
  return value;
}

function cityPoint(cityName) {
  return (state.frontend.home.heatmap_points || []).find((x) => x.name === cityName);
}

function poiBaseRows() {
  return state.frontend?.filter_panel?.sample_poi || [];
}

function impactProvinces() {
  return [...new Set(poiBaseRows().map((row) => String(row.province || "").trim()).filter(Boolean))].sort();
}

function impactCities(province = "") {
  return [...new Map(
    poiBaseRows()
      .filter((row) => !province || row.province === province)
      .map((row) => [row.city_name, { city_name: row.city_name, province: row.province }])
  ).values()].filter((row) => row.city_name).sort((a, b) => String(a.city_name).localeCompare(String(b.city_name)));
}

function impactPois(province = "", city = "") {
  return poiBaseRows()
    .filter((row) => (!province || row.province === province) && (!city || row.city_name === city))
    .slice()
    .sort((a, b) => Number(b.heat_score || 0) - Number(a.heat_score || 0));
}

function impactPoiMatch() {
  const province = state.impactProvince || "";
  const city = state.impactCity || "";
  const poi = state.impactPoi || "";
  if (!poi) return null;
  return fuzzyPick(impactPois(province, city), poi, ["poi_name", "region_name", "tag_text", "short_feature"])[0] || null;
}

function findImpactCitySummary(cityName) {
  return (state.flow?.impact?.city_impact_top20 || []).find((row) => row.city_name === cityName) || null;
}

function impactHolidayTier(value) {
  const ratio = Number(value || 0);
  if (ratio >= 1.5) return "假期拉动非常明显";
  if (ratio >= 1.2) return "假期拉动较强";
  if (ratio >= 0.9) return "假期拉动中等";
  return "假期拉动相对平缓";
}

function impactRainTier(value) {
  const ratio = Number(value || 0);
  if (ratio >= 0.58) return "雨天回落明显";
  if (ratio >= 0.45) return "雨天有一定影响";
  return "雨天影响相对温和";
}

function impactVisitWindow(poi, heatScore) {
  const distance = String(poi?.distance_level || "");
  const tags = String(poi?.tag_text || "");
  if (tags.includes("夜游")) return "建议 17:00 后进入核心游览时段，白天安排周边轻量行程";
  if (heatScore >= 7.5 || distance === "市中心") return "建议 09:30 前入场，中午后切换到室内或街区型活动";
  if (distance === "远郊") return "建议上午整块安排，避免下午返程拥堵";
  return "建议上午优先游览热门点位，下午安排拍照、休闲或餐饮";
}

function impactRainPlan(poi, rain, cityRainRatio) {
  const tags = String(poi?.tag_text || "");
  const feature = String(poi?.short_feature || "");
  const indoorFriendly = ["博物馆", "展馆", "古镇", "街区", "美食", "文化"].some((key) => tags.includes(key) || feature.includes(key));
  if (rain >= 10 || cityRainRatio >= 0.55) {
    return indoorFriendly
      ? "雨天仍可保留主行程，但建议压缩户外停留时间，把拍照和步行段改到雨势较弱时段。"
      : "遇到降水建议准备室内替代路线，优先切换到展馆、商圈或餐饮街区，避免长时间户外排队。";
  }
  return indoorFriendly
    ? "小雨条件下可正常出行，建议备伞并把核心参观点放在前半程。"
    : "当前降水压力不大，可以正常安排户外游览，但热门景点仍建议错峰。";
}

function impactAudienceText(poi) {
  const tags = String(poi?.tag_text || "");
  if (tags.includes("亲子")) return "更适合亲子家庭、轻松节奏出游人群。";
  if (tags.includes("夜游")) return "适合年轻游客、周末打卡和夜间社交出行。";
  if (tags.includes("历史") || tags.includes("人文")) return "适合文化体验、慢游和讲解导览型游客。";
  if (tags.includes("山水") || tags.includes("自然")) return "适合摄影、休闲观景和周边短途游客。";
  return "适合作为城市出行中的通用候选景点，根据节假日和天气灵活调整。";
}

function updateImpactProvinceOptions() {
  $("impactProvinceOptions").innerHTML = impactProvinces().map((item) => `<option value="${html(item)}"></option>`).join("");
}

function updateImpactCityOptions() {
  const cities = fuzzyPick(impactCities(state.impactProvince), $("impactCityInput")?.value || "", ["city_name", "province"]).slice(0, 24);
  $("impactCityOptions").innerHTML = cities.map((item) => `<option value="${html(item.city_name)}" label="${html(item.province || "")}"></option>`).join("");
}

function updateImpactPoiOptions() {
  const pois = fuzzyPick(impactPois(state.impactProvince, state.impactCity), $("impactPoiInput")?.value || "", ["poi_name", "region_name", "tag_text", "short_feature"]).slice(0, 30);
  $("impactPoiOptions").innerHTML = pois.map((item) => `<option value="${html(item.poi_name)}" label="${html(`${item.city_name || ""} ${item.region_name || ""}`.trim())}"></option>`).join("");
}

function updateImpactInputsState() {
  $("impactCityInput").disabled = !state.impactProvince;
  $("impactPoiInput").disabled = !state.impactCity;
}

function buildImpactSelector() {
  if (!$("impactProvinceInput")) return;
  const provinces = impactProvinces();
  if (!state.impactProvince) state.impactProvince = provinces[0] || "";
  if (!state.impactCity && state.impactProvince) state.impactCity = impactCities(state.impactProvince)[0]?.city_name || "";
  if (!state.impactPoi && state.impactProvince && state.impactCity) state.impactPoi = impactPois(state.impactProvince, state.impactCity)[0]?.poi_name || "";
  $("impactProvinceInput").value = state.impactProvince;
  $("impactCityInput").value = state.impactCity;
  $("impactPoiInput").value = state.impactPoi;
  updateImpactProvinceOptions();
  updateImpactCityOptions();
  updateImpactPoiOptions();
  updateImpactInputsState();
  $("impactProvinceInput").addEventListener("input", () => {
    const value = $("impactProvinceInput").value.trim();
    const matched = impactProvinces().find((item) => item === value);
    state.impactProvince = matched || value;
    state.impactCity = "";
    state.impactPoi = "";
    $("impactCityInput").value = "";
    $("impactPoiInput").value = "";
    updateImpactCityOptions();
    updateImpactPoiOptions();
    updateImpactInputsState();
  });
  $("impactCityInput").addEventListener("input", () => {
    const value = $("impactCityInput").value.trim();
    const matched = fuzzyPick(impactCities(state.impactProvince), value, ["city_name", "province"])[0];
    state.impactCity = matched?.city_name || value;
    state.impactPoi = "";
    $("impactPoiInput").value = "";
    updateImpactPoiOptions();
    updateImpactInputsState();
  });
  $("impactPoiInput").addEventListener("input", () => {
    state.impactPoi = $("impactPoiInput").value.trim();
    updateImpactPoiOptions();
  });
  $("impactAnalyzeButton").addEventListener("click", () => renderImpact(true));
}

function ensureImpactSelection() {
  const provinces = impactProvinces();
  if (!state.impactProvince || !provinces.includes(state.impactProvince)) {
    state.impactProvince = provinces[0] || "";
  }
  const cities = impactCities(state.impactProvince);
  if (!state.impactCity || !cities.some((item) => item.city_name === state.impactCity)) {
    state.impactCity = cities[0]?.city_name || "";
  }
  const pois = impactPois(state.impactProvince, state.impactCity);
  if (!state.impactPoi || !pois.some((item) => item.poi_name === state.impactPoi)) {
    state.impactPoi = pois[0]?.poi_name || "";
  }
  if ($("impactProvinceInput")) $("impactProvinceInput").value = state.impactProvince;
  if ($("impactCityInput")) $("impactCityInput").value = state.impactCity;
  if ($("impactPoiInput")) $("impactPoiInput").value = state.impactPoi;
  if ($("impactProvinceOptions")) updateImpactProvinceOptions();
  if ($("impactCityOptions")) updateImpactCityOptions();
  if ($("impactPoiOptions")) updateImpactPoiOptions();
  if ($("impactCityInput") && $("impactPoiInput")) updateImpactInputsState();
}

async function loadCityLiveWeather(cityName) {
  const point = cityPoint(cityName);
  if (!point) return null;
  try {
    return await fetchJson(`/api/weather/current?lat=${point.lat}&lon=${point.lng}`);
  } catch {
    return null;
  }
}

function renderFlow() {
  const report = state.flow.report || {};
  const evaluation = report.evaluation || {};
  const summary = report.input_summary || {};
  $("flowSummaryCards").innerHTML = [
    ["训练样本总数", summary.row_count],
    ["训练集", summary.full_train_row_count || summary.train_row_count],
    ["测试集", summary.full_test_row_count || summary.test_row_count],
    ["R²", dec(evaluation.r2, 4)],
    ["MAE", dec(evaluation.mae, 0)],
    ["数据日期", summary.date_range || "-"],
  ].map(([a, b]) => `<span><strong>${metricDisplay(a, b)}</strong>${a}</span>`).join("");
  const modelName = html(report.model_summary?.model_name || "XGBoost 回归模型");
  const splitNote = html(summary.split_note || "训练集用于学习规律，测试集用于检验预测误差");
  const topFeatures = (report.model_summary?.top_feature_effects || []).slice(0, 4);
  $("flowModelNote").innerHTML = `
    <strong>${modelName}</strong>
    <p>模型使用景点基础信息、天气、节假日、日期特征和历史客流特征进行预测。${splitNote}</p>
    ${topFeatures.length ? `<div class="poi-meta">${topFeatures.map((item) => `<span>${html(item.feature_name)} ${dec(Number(item.importance || 0) * 100, 1)}%</span>`).join("")}</div>` : ""}
  `;
  const cityRows = (state.flow.forecast.city_7day || []).filter((x) => x.city_name === state.forecastCity).sort((a, b) => String(a.forecast_date).localeCompare(String(b.forecast_date)));
  const selectedDate = $("forecastDateSelector").value || cityRows[0]?.forecast_date || "";
  $("forecastTrendTitle").textContent = `${state.forecastCity || "城市"}未来 7 天客流`;
  setLine("forecastTrendChart", cityRows.map((x) => x.forecast_date), cityRows.map((x) => x.forecast_flow), palette.red);
  $("forecastCityBody").innerHTML = cityRows.map((row) => `<tr><td>${html(row.forecast_date)}</td><td>${fmt(row.forecast_flow)}</td><td>${fmt(row.poi_count)}</td><td>${dec(displayTemperature(row), 1)}℃</td><td>${dec(row.avg_precipitation, 1)}mm</td></tr>`).join("");
  const cityPoiRows = (state.flow.forecast.future_7day || [])
    .filter((row) => row.city_name === state.forecastCity && (!selectedDate || row.forecast_date === selectedDate))
    .sort((a, b) => Number(b.forecast_flow || 0) - Number(a.forecast_flow || 0))
    .slice(0, 12);
  $("forecastPeakBody").innerHTML = cityPoiRows.length
    ? cityPoiRows.map((row) => `<tr><td>${html(row.poi_name)}</td><td>${html(row.city_name)}</td><td>${html(row.forecast_date)}</td><td>${fmt(row.forecast_flow)}</td><td>${html(row.forecast_level)}</td></tr>`).join("")
    : `<tr><td colspan="5">当前城市和日期暂无景点级预测明细</td></tr>`;
  renderFlowAdvice(cityRows);
}

function renderFlowAdvice(cityRows) {
  const selected = $("forecastDateSelector").value;
  const target = cityRows.find((x) => String(x.forecast_date).startsWith(selected)) || cityRows[0] || {};
  const maxFlow = Math.max(...cityRows.map((x) => Number(x.forecast_flow || 0)), 1);
  const level = Number(target.forecast_flow || 0) > maxFlow * 0.86 ? "偏高" : Number(target.forecast_flow || 0) < maxFlow * 0.55 ? "偏低" : "平稳";
  const rain = Number(target.avg_precipitation || 0);
  const temp = dec(displayTemperature(target), 1);
  $("flowAdviceBox").innerHTML = `
    <h3>出行建议</h3>
    <div class="flow-advice-header">
      <strong>${html(state.forecastCity || "-")} · ${html(target.forecast_date || selected || "-")}</strong>
      <span class="flow-level-chip ${level === "偏高" ? "warn" : level === "偏低" ? "calm" : ""}">${level}</span>
    </div>
    <div class="poi-meta">
      <span>预测客流 ${fmt(target.forecast_flow)}</span>
      <span>覆盖景点 ${fmt(target.poi_count || 0)}</span>
      <span>温度 ${temp}℃</span>
      <span>降水 ${dec(rain, 1)}mm</span>
    </div>
    <p id="flowLiveWeather" class="flow-live-weather">正在读取实时天气...</p>
    <p>${rain > 8 ? "预计降水较明显，建议把博物馆、室内展馆、商圈美食安排到雨势较大的时段，户外山水类景点尽量压缩停留时间。" : "降水影响较小，可以正常安排户外景点；如果是热门景区，建议上午入园，下午安排街区、美食或轻量休闲项目。"}</p>
    <p>如果当天接近周末或节假日，建议提前完成门票预约和交通规划；同行有老人或儿童时，优先选择交通方便、步行压力较低的景点。高峰预警表中的景点可作为重点避峰对象，尽量错开 10:30-15:30 的集中到访时段。</p>
  `;
  loadCityLiveWeather(state.forecastCity).then((weather) => {
    const el = $("flowLiveWeather");
    if (!el) return;
    if (!weather || weather.temperature === null || weather.temperature === undefined) {
      el.textContent = "实时天气暂不可用";
      return;
    }
    el.textContent = `实时天气：${weather.weather || "当前"}，${dec(weather.temperature, 1)}℃`;
  });
}

function renderImpact() {
  const impact = state.flow.impact;
  const weatherImpactChart = state.charts.flowImpactChart;
  if (weatherImpactChart) {
    const names = impact.weather_holiday_summary.map((x) => x.group_name);
    const values = impact.weather_holiday_summary.map((x) => Number(x.avg_flow || 0));
    weatherImpactChart.setOption({
      ...baseChart(),
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      grid: { left: 146, right: 54, top: 24, bottom: 24, containLabel: true },
      xAxis: {
        type: "value",
        max: (value) => Math.ceil((Number(value.max || 0) * 1.08) / 5000) * 5000,
        splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
      },
      yAxis: {
        type: "category",
        data: names,
        inverse: true,
        axisLabel: { width: 122, overflow: "truncate", margin: 12 },
      },
      series: [{
        type: "bar",
        data: values,
        barMaxWidth: 28,
        itemStyle: {
          borderRadius: [0, 12, 12, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: palette.blue }, { offset: 1, color: palette.teal }]),
        },
      }],
    }, true);
  }
  const holidayTypeChart = state.charts.holidayTypeChart;
  if (holidayTypeChart) {
    const names = impact.holiday_type_summary.map((x) => x.holiday_name);
    const values = impact.holiday_type_summary.map((x) => Number(x.avg_flow || 0));
    holidayTypeChart.setOption({
      ...baseChart(),
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (params) => {
          const item = params?.[0];
          return item ? `${item.name}<br>日均客流：${fmt(item.value)}` : "";
        },
      },
      grid: { left: 116, right: 60, top: 24, bottom: 24, containLabel: true },
      xAxis: {
        type: "value",
        max: (value) => Math.ceil((Number(value.max || 0) * 1.1) / 5000) * 5000,
        splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } },
      },
      yAxis: {
        type: "category",
        data: names,
        inverse: true,
        axisLabel: { width: 96, overflow: "truncate", margin: 10 },
      },
      series: [{
        type: "bar",
        data: values,
        barMaxWidth: 28,
        itemStyle: {
          borderRadius: [0, 12, 12, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: palette.orange }, { offset: 1, color: palette.red }]),
        },
      }],
    }, true);
  }
  if (!state.impactProvince && !state.impactCity && !state.impactPoi) buildImpactSelector();
  ensureImpactSelection();
  const cityRows = (impact.city_impact_top20 || []).slice(0, 12);
  if ($("impactExplainBox")) {
    $("impactExplainBox").innerHTML = `
      <h3>口径说明</h3>
      <p>当前城市榜并不是单独按“天气影响”排序，而是先按 <strong>节假日较平日增幅</strong> 排序，再同时展示 <strong>雨天回落</strong> 作为敏感度参考。</p>
      <div class="poi-meta">
        <span>排序口径 较平日增幅优先</span>
        <span>展示范围 TOP ${fmt(cityRows.length)}</span>
        <span>用途 运营巡检与活动选城</span>
      </div>
    `;
  }
  if ($("impactMeaningBox")) {
    $("impactMeaningBox").innerHTML = `
      <h3>这些指标怎么看</h3>
      <p><strong>较平日增幅</strong> 的公式是 <code>(节假日客流 - 平日客流) / 平日客流</code>。所以 167.8% 的意思是“节假日日均客流比平日日均客流高 167.8%”，不是天气百分比。</p>
      <p><strong>雨天回落</strong> 表示下雨天气对客流的压制程度，越高说明越容易受雨天影响。</p>
      <p><strong>平均客流</strong> 是当前城市近 7 日预测客流均值，用来判断它本身是不是大盘量级城市。</p>
      <p><strong>清明节偏高</strong> 这里比较的是不同节日的<strong>日均客流</strong>，不是节日总客流。像清明这种短途踏青、周边出游集中的节日，在华东样本里日均值偏高是可能出现的。</p>
      <p><strong>未进入 TOP 样本</strong> 的意思不是没有影响，而是它没有排进当前这张展示榜的前列，所以这里会优先参考实时天气、近 7 日客流和景点热度。</p>
    `;
  }
  if ($("impactSelectionNote")) {
    const path = [state.impactProvince, state.impactCity, state.impactPoi].filter(Boolean).join(" / ");
    $("impactSelectionNote").textContent = path ? `当前分析对象：${path}` : "先完成省份、城市、景点选择，再查看下方分析结果";
  }
  if (state.charts.impactCityRankChart) {
    state.charts.impactCityRankChart.setOption({
      ...baseChart(),
      tooltip: {
        formatter: (params) => {
          const row = cityRows[params.dataIndex] || {};
          return `${html(row.city_name || "-")}<br>较平日增幅：${pct(row.holiday_lift_ratio)}<br>雨天回落：${pct(row.rain_drop_ratio)}<br>平均客流：${fmt(row.avg_flow)}`;
        },
      },
      grid: { left: 92, right: 46, top: 18, bottom: 20 },
      xAxis: { type: "value", axisLabel: { formatter: (value) => `${value}%` }, splitLine: { lineStyle: { color: "rgba(69,108,84,.12)" } } },
      yAxis: { type: "category", data: cityRows.map((row) => row.city_name), inverse: true, axisLabel: { color: "#456c54" } },
      series: [{
        type: "bar",
        data: cityRows.map((row) => Number(row.holiday_lift_ratio || 0) * 100),
        barWidth: 18,
        itemStyle: {
          borderRadius: [0, 10, 10, 0],
          color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [{ offset: 0, color: "#d17f63" }, { offset: 1, color: "#7fb16f" }]),
        },
        label: { show: true, position: "right", color: "#4a5f4d", formatter: (params) => `${dec(params.value, 1)}%` },
      }],
    }, true);
    state.charts.impactCityRankChart.off("click");
    state.charts.impactCityRankChart.on("click", (params) => {
      const row = cityRows[params.dataIndex];
      if (!row) return;
      const matched = impactCities().find((item) => item.city_name === row.city_name);
      state.impactProvince = matched?.province || state.impactProvince;
      state.impactCity = row.city_name || "";
      state.impactPoi = impactPois(state.impactProvince, state.impactCity)[0]?.poi_name || "";
      $("impactProvinceInput").value = state.impactProvince;
      $("impactCityInput").value = state.impactCity;
      $("impactPoiInput").value = state.impactPoi;
      updateImpactCityOptions();
      updateImpactPoiOptions();
      updateImpactInputsState();
      renderImpact(true);
    });
  }
  $("impactCityBody").innerHTML = cityRows.map((row) => `<tr class="impact-city-row ${row.city_name === state.impactCity ? "selected" : ""}" data-impact-city="${html(row.city_name)}"><td>${html(row.city_name)}</td><td>${pct(row.holiday_lift_ratio)}</td><td>${pct(row.rain_drop_ratio)}</td><td>${fmt(row.avg_flow)}</td></tr>`).join("");
  document.querySelectorAll("[data-impact-city]").forEach((rowEl) => rowEl.addEventListener("click", () => {
    const cityName = rowEl.dataset.impactCity || "";
    const matched = impactCities().find((item) => item.city_name === cityName);
    state.impactProvince = matched?.province || state.impactProvince;
    state.impactCity = cityName;
    state.impactPoi = impactPois(state.impactProvince, state.impactCity)[0]?.poi_name || "";
    $("impactProvinceInput").value = state.impactProvince;
    $("impactCityInput").value = state.impactCity;
    $("impactPoiInput").value = state.impactPoi;
    updateImpactCityOptions();
    updateImpactPoiOptions();
    updateImpactInputsState();
    renderImpact(true);
  }));
  renderImpactDrilldown();
}

function renderImpactDrilldown() {
  const poi = impactPoiMatch();
  const city = state.impactCity || poi?.city_name || "";
  const province = state.impactProvince || poi?.province || "";
  const citySummary = findImpactCitySummary(city);
  const cityRows = (state.flow?.forecast?.city_7day || []).filter((row) => row.city_name === city);
  const avgTemp = cityRows.length ? cityRows.reduce((sum, row) => sum + Number(displayTemperature(row) || 0), 0) / cityRows.length : 0;
  const avgRain = cityRows.length ? cityRows.reduce((sum, row) => sum + Number(row.avg_precipitation || 0), 0) / cityRows.length : 0;
  const avgFlow = cityRows.length ? cityRows.reduce((sum, row) => sum + Number(row.forecast_flow || 0), 0) / cityRows.length : Number(citySummary?.avg_flow || 0);
  const nearbyPois = impactPois(province, city).slice(0, 18);
  const hasImpactSample = Boolean(citySummary);
  const heatScore = Number(poi?.heat_score || 0);
  const commentScore = Number(poi?.comment_score || 0);
  const holidayTier = impactHolidayTier(citySummary?.holiday_lift_ratio || 0);
  const rainTier = impactRainTier(citySummary?.rain_drop_ratio || 0);
  const visitWindow = impactVisitWindow(poi, heatScore);
  const rainPlan = impactRainPlan(poi, avgRain, citySummary?.rain_drop_ratio || 0);
  const audienceText = impactAudienceText(poi);
  if ($("impactDetailBox")) {
    if (!city) {
      $("impactDetailBox").innerHTML = `<div class="plan-empty">请先按省份 -> 城市 -> 景点选择后，再查看详细天气影响分析。</div>`;
    } else {
      const distance = poi?.distance_level || "距离待补充";
      const tags = String(poi?.tag_text || "").split(/[|,，]/).map((item) => item.trim()).filter(Boolean).slice(0, 4);
      const relatedPois = nearbyPois.filter((row) => row.poi_name !== poi?.poi_name).slice(0, 4);
      $("impactDetailBox").innerHTML = `
        <h3>${html(poi?.poi_name || city)}</h3>
        <p>${html([province, city, poi?.region_name || ""].filter(Boolean).join(" / "))}</p>
        <div class="impact-metric-grid">
          <span><strong>${hasImpactSample ? pct(citySummary?.holiday_lift_ratio || 0) : "未进入TOP样本"}</strong>较平日增幅</span>
          <span><strong>${hasImpactSample ? pct(citySummary?.rain_drop_ratio || 0) : "未进入TOP样本"}</strong>雨天回落</span>
          <span><strong>${fmt(avgFlow)}</strong>平均客流</span>
          <span><strong>${dec(avgTemp, 1)}℃</strong>近 7 日均温</span>
          <span><strong>${dec(avgRain, 1)}mm</strong>近 7 日降水</span>
          <span><strong>${html(distance)}</strong>距离层级</span>
        </div>
        ${poi ? `<div class="poi-meta"><span>评分 ${dec(poi.comment_score || 0)}</span><span>热度 ${dec(poi.heat_score || 0)}</span><span>评论 ${fmt(poi.comment_count || 0)}</span>${tags.map((tag) => `<span>${html(tag)}</span>`).join("")}</div>` : ""}
        <p id="impactLiveWeather" class="flow-live-weather">正在读取实时天气...</p>
        <p>${poi?.short_feature ? html(poi.short_feature) : "当前详细分析优先结合城市天气敏感度、景点热度和游客评分，帮助运营判断节假日投放与雨天备选策略。"}</p>
        ${hasImpactSample ? "" : `<p class="hint-text">当前城市不在节假日/雨天影响 TOP 榜样本中，下方建议优先参考实时天气、近 7 日客流和景点热度。</p>`}
        <div class="impact-strength-list">
          <div><label>假期拉动</label><b style="width:${hasImpactSample ? Math.min(100, Math.max(8, Number(citySummary?.holiday_lift_ratio || 0) * 60)) : 16}%"></b></div>
          <div><label>雨天敏感</label><b class="warn" style="width:${hasImpactSample ? Math.min(100, Math.max(8, Number(citySummary?.rain_drop_ratio || 0) * 100)) : 16}%"></b></div>
          <div><label>景点热度</label><b class="teal" style="width:${Math.min(100, Math.max(8, Number(poi?.heat_score || 0) * 10))}%"></b></div>
        </div>
        <div class="impact-advice-grid">
          <section><strong>假期判断</strong><p>${html(hasImpactSample ? `${holidayTier}，这里的 ${pct(citySummary?.holiday_lift_ratio || 0)} 表示“较平日日均客流增加了这么多”，${fmt(avgFlow)} 左右的平均客流说明它更适合做假期重点运营或提前分流提醒。` : `当前更适合先参考平均客流 ${fmt(avgFlow)} 与景点热度判断运营优先级，节假日弹性需要更多样本支撑。`)}</p></section>
          <section><strong>天气判断</strong><p>${html(hasImpactSample ? `${rainTier}。${rainPlan}` : rainPlan)}</p></section>
          <section><strong>游览节奏</strong><p>${html(visitWindow)}</p></section>
          <section><strong>适合人群</strong><p>${html(audienceText)}</p></section>
        </div>
        ${relatedPois.length ? `<div class="impact-related-box"><strong>同城可联动景点</strong><ul class="tip-list compact-list">${relatedPois.map((row) => `<li>${html(row.poi_name)} · 热度 ${dec(row.heat_score || 0)} · 评分 ${dec(row.comment_score || 0)}</li>`).join("")}</ul></div>` : ""}
      `;
      loadCityLiveWeather(city).then((weather) => {
        const el = $("impactLiveWeather");
        if (!el) return;
        if (!weather || weather.temperature === null || weather.temperature === undefined) {
          el.textContent = "实时天气暂不可用";
          return;
        }
        const windText = windSummary(weather) || "风力信息暂缺";
        el.textContent = `实时天气：${weather.weather || "当前"}，${dec(weather.temperature, 1)}℃，${windText}`;
      });
    }
  }
}

function provinceCompetitionRows() {
  const rows = (state.frontend?.region_dashboard?.province_summary || []).map((row) => {
    const poiCount = Number(row.poi_count || 0);
    const cityCount = Number(row.city_count || 0);
    const avgHeat = Number(row.avg_heat || 0);
    const avgScore = Number(row.avg_score || 0);
    const commentTotal = Number(row.comment_total || 0);
    const freeRatio = freeRatioOf(row);
    const highScoreRatio = Number(row.high_score_ratio || (Number(row.high_score_poi_count || 0) / Math.max(poiCount, 1)));
    const fiveARatio = Number(row.five_a_poi_count || 0) / Math.max(poiCount, 1);
    return {
      ...row,
      poiCount,
      cityCount,
      avgHeat,
      avgScore,
      commentTotal,
      freeRatio,
      highScoreRatio,
      fiveARatio,
    };
  });
  const maxPoi = Math.max(...rows.map((row) => row.poiCount), 1);
  const maxHeat = Math.max(...rows.map((row) => row.avgHeat), 1);
  const maxScore = Math.max(...rows.map((row) => row.avgScore), 1);
  const maxComments = Math.max(...rows.map((row) => row.commentTotal), 1);
  return rows
    .map((row) => ({
      ...row,
      competitionScore: Number((
        row.poiCount / maxPoi * 28
        + row.avgHeat / maxHeat * 24
        + row.avgScore / maxScore * 18
        + row.commentTotal / maxComments * 16
        + row.highScoreRatio * 8
        + row.fiveARatio * 4
        + row.freeRatio * 2
      ).toFixed(1)),
    }))
    .sort((a, b) => b.competitionScore - a.competitionScore);
}

function provinceCompetitionInsight(row, rank) {
  const strengths = [];
  if (row.avgHeat >= 4.1) strengths.push("热度外溢强");
  if (row.avgScore >= 3.7) strengths.push("口碑基础稳");
  if (row.highScoreRatio >= 0.5) strengths.push("高评分景点占比较高");
  if (row.freeRatio >= 0.72) strengths.push("免费景点友好");
  if (row.fiveARatio >= 0.018) strengths.push("高等级景区支撑明显");
  const lead = strengths[0] || "整体资源较均衡";
  const follow = strengths[1] || "适合继续做结构优化";
  return { lead, follow, text: `第 ${rank} 位 · ${lead}，${follow}。` };
}

function topPoiByProvince(province) {
  const rows = state.frontend?.region_dashboard?.province_top_poi?.[province] || [];
  return rows.slice().sort((a, b) => compositeScore(b) - compositeScore(a))[0] || null;
}

function provinceTagLeaders(rows) {
  return rows
    .map((row) => {
      const topTags = provinceTagRows(row.province).slice(0, 2);
      return {
        province: row.province,
        primaryTag: topTags[0]?.tag_name || "主题待补充",
        primaryCount: Number(topTags[0]?.poi_count || 0),
        secondaryTag: topTags[1]?.tag_name || "",
      };
    })
    .sort((a, b) => b.primaryCount - a.primaryCount);
}

function renderCluster() {
  const rows = provinceCompetitionRows();
  setBar("clusterSummaryChart", rows.map((row) => row.province), rows.map((row) => row.competitionScore), true, [palette.green, palette.teal]);
  setScatter(
    "clusterProfileChart",
    rows,
    (row) => Number(row.avgHeat || 0),
    (row) => Number(row.avgScore || 0),
    (row) => Math.max(480, Number(row.poiCount || 0) * 4),
    "平均热度",
    "平均评分",
    palette.brown,
  );
  const topRows = rows.slice(0, 3);
  const otherRows = rows.slice(3);
  const renderProvinceCard = (row, index) => `
    <article class="province-competition-card">
      <div class="province-card-top">
        <div>
          <strong>${html(row.province)}</strong>
          <span class="province-card-subtitle">${fmt(row.poiCount)} 个景点 · ${fmt(row.cityCount)} 个城市</span>
        </div>
        <b class="province-rank-badge">第 ${index + 1} 位</b>
      </div>
      <div class="province-score-row">
        <label>综合得分</label>
        <strong>${dec(row.competitionScore, 1)}</strong>
      </div>
      <div class="province-metric-grid">
        <span><b>${dec(row.avgHeat, 2)}</b>平均热度</span>
        <span><b>${dec(row.avgScore, 2)}</b>平均评分</span>
        <span><b>${pct(row.freeRatio)}</b>免费占比</span>
        <span><b>${pct(row.highScoreRatio)}</b>高评占比</span>
      </div>
      <div class="province-insight-box">
        <em>${html(provinceCompetitionInsight(row, index + 1).lead)}</em>
        <p>${html(provinceCompetitionInsight(row, index + 1).text)}</p>
      </div>
    </article>
  `;
  $("clusterCards").innerHTML = `
    <div class="cluster-cards-row cluster-cards-row-top">${topRows.map((row, index) => renderProvinceCard(row, index)).join("")}</div>
    <div class="cluster-cards-row cluster-cards-row-bottom">${otherRows.map((row, index) => renderProvinceCard(row, index + 3)).join("")}</div>
  `;
  $("clusterTopPoiBoard").innerHTML = rows.map((row) => {
    const poi = topPoiByProvince(row.province);
    if (!poi) {
      return `<article class="province-top-poi-item"><strong>${html(row.province)}</strong><p>暂无代表景点数据</p></article>`;
    }
    return `
      <article class="province-top-poi-item">
        <div>
          <strong>${html(row.province)}</strong>
          <h4>${html(poi.poi_name || "-")}</h4>
        </div>
        <p>${html(poi.city_name || "-")} / ${html(poi.region_name || poi.district_name || "景区")}</p>
        <div class="poi-meta"><span>热度 ${dec(poi.heat_score || 0)}</span><span>评分 ${dec(poi.comment_score || 0)}</span><span>评论 ${fmt(poi.comment_count || 0)}</span></div>
      </article>
    `;
  }).join("");
  const tagLeaders = provinceTagLeaders(rows);
  setBar("clusterTagCompareChart", tagLeaders.map((row) => `${row.province} · ${row.primaryTag}`), tagLeaders.map((row) => row.primaryCount), true, [palette.orange, palette.red]);
  $("trainingReportBox").innerHTML = "";
  $("trainingReportBox").classList.add("hidden");
}

async function renderPortrait(force = false) {
  if (!state.portrait || force) state.portrait = await fetchJson("/api/admin/user-portrait");
  const interaction = state.portrait.interaction || {};
  $("interactionCards").innerHTML = [
    ["评论总数", interaction.comment_count || 0],
    ["评论用户：", interaction.comment_user_count || 0],
    ["平均评分", interaction.avg_rating || 0],
    ["用户分层：", state.portrait.segments.length],
  ].map(([a, b]) => `<span><strong>${b}</strong>${a}</span>`).join("");
  setPie("portraitSegmentChart", state.portrait.segments, "segment_name", "user_count");
  setBar("portraitPreferenceChart", state.portrait.preferences.map((x) => x.preference_tag), state.portrait.preferences.map((x) => x.user_count), true, [palette.green, palette.teal]);
  const cityRows = state.portrait.comment_cities?.length ? state.portrait.comment_cities : state.portrait.cities;
  setBar("portraitCityChart", cityRows.map((x) => x.city_name), cityRows.map((x) => x.comment_count || x.user_count), true, [palette.red, palette.orange]);
  setPie("portraitAgeChart", state.portrait.ages, "age_group", "user_count", [palette.blue, palette.teal, palette.orange, palette.red]);
  renderWordCloud();
  await loadAdminUsers();
  if (state.appView === "dashboard") renderBigScreen();
}

function renderWordCloud() {
  const rows = state.portrait.word_cloud || [];
  const sortedRows = rows
    .map((row) => ({ name: row.name, value: Number(row.value || 0) }))
    .filter((row) => row.name && row.value > 0)
    .sort((a, b) => b.value - a.value);
  const max = Math.max(...sortedRows.map((x) => x.value), 1);
  const min = Math.min(...sortedRows.map((x) => x.value), max);
  const chartRows = sortedRows.map((row, index) => {
    const ratio = max === min ? 1 : (row.value - min) / Math.max(max - min, 1);
    const boosted = Math.pow(Math.max(ratio, 0), 1.6);
    const rankBonus = Math.max(0, 1 - index / Math.max(sortedRows.length - 1, 1));
    return {
      ...row,
      rawValue: row.value,
      value: Math.round(16 + boosted * 68 + rankBonus * 12),
    };
  });
  if (state.charts.portraitWordCloudChart && rows.length) {
    state.charts.portraitWordCloudChart.setOption({
      ...baseChart(),
      tooltip: {
        formatter: (params) => `${params.name}<br>提及次数：${fmt(params.data.rawValue || params.data.value || 0)}`,
      },
      series: [{
        type: "wordCloud",
        shape: "circle",
        left: "center",
        top: "center",
        width: "95%",
        height: "92%",
        sizeRange: [12, 80],
        rotationRange: [-45, 45],
        rotationStep: 15,
        gridSize: 12,
        drawOutOfBound: false,
        textStyle: {
          fontFamily: "Microsoft YaHei",
          fontWeight: 800,
          color() {
            const colors = [palette.red, palette.orange, palette.green, palette.blue, palette.brown, palette.rose];
            return colors[Math.floor(Math.random() * colors.length)];
          },
        },
        data: chartRows,
      }],
    });
    $("portraitWordCloud").classList.add("hidden");
  }
  $("portraitWordCloud").innerHTML = chartRows.map((row, index) => {
    const size = 12 + Math.round((Number(row.value || 1) / Math.max(...chartRows.map((x) => Number(x.value || 1)), 1)) * 64);
    const colors = [palette.red, palette.orange, palette.green, palette.blue, palette.brown, palette.rose];
    return `<span style="font-size:${size}px;color:${colors[index % colors.length]}">${html(row.name)}</span>`;
  }).join("");
  if ($("portraitAlgoNote")) {
    $("portraitAlgoNote").innerHTML = `<h3>算法说明</h3>${(state.portrait.algorithm_notes || []).map((x) => `<p><strong>${html(x.name)}</strong>${html(x.principle)}</p>`).join("")}`;
  }
}

async function loadAdminUsers() {
  if (state.role !== "operator") return;
  state.adminUsers = await fetchJson("/api/admin/users").catch(() => []);
  const rows = state.adminUsers || [];
  const renderUserRows = (list, allowDelete = true) => list.length ? list.map((row) => `
    <tr>
      <td>${html(row.username)}</td>
      <td>${row.role === "operator" ? "管理员" : "游客"}</td>
      <td>${html(row.nickname || "-")}</td>
      <td>${html(row.city_name || "-")}</td>
      <td>${html(row.travel_preference || "-")}</td>
      <td>${fmt(row.favorite_count || 0)}</td>
      <td>${fmt(row.comment_count || 0)}</td>
      <td><button class="mini-button" data-edit-user="${row.id}">编辑</button>${allowDelete && row.role !== "operator" ? `<button class="mini-button danger" data-delete-user="${row.id}">删除</button>` : ""}</td>
    </tr>
  `).join("") : `<tr><td colspan="8">暂无账号数据</td></tr>`;
  const operatorRows = rows.filter((row) => row.role === "operator");
  const touristRows = rows.filter((row) => row.role !== "operator");
  if ($("adminOperatorCount")) $("adminOperatorCount").textContent = fmt(operatorRows.length);
  if ($("adminTouristCount")) $("adminTouristCount").textContent = fmt(touristRows.length);
  if ($("adminOperatorBody")) $("adminOperatorBody").innerHTML = renderUserRows(operatorRows, false);
  $("adminUserBody").innerHTML = renderUserRows(touristRows, true);
  document.querySelectorAll("[data-edit-user]").forEach((btn) => btn.addEventListener("click", () => editAdminUser(btn.dataset.editUser)));
  document.querySelectorAll("[data-delete-user]").forEach((btn) => btn.addEventListener("click", () => deleteAdminUser(btn.dataset.deleteUser)));
  await loadAdminComments();
}

async function createAdminUser() {
  const params = new URLSearchParams({
    username: $("adminNewUsername").value.trim(),
    password: $("adminNewPassword").value.trim() || "123456",
    nickname: $("adminNewNickname").value.trim(),
    city_name: $("adminNewCity").value.trim(),
    role: $("adminNewRole").value,
  });
  state.adminUsers = await fetchJson(`/api/admin/create-user?${params.toString()}`);
  ["adminNewUsername", "adminNewPassword", "adminNewNickname", "adminNewCity"].forEach((id) => ($(id).value = ""));
  await loadAdminUsers();
}

async function editAdminUser(userId) {
  const user = (state.adminUsers || []).find((x) => String(x.id) === String(userId));
  if (!user) return;
  const nickname = prompt("修改昵称", user.nickname || "");
  if (nickname === null) return;
  const city = prompt("修改城市", user.city_name || "");
  if (city === null) return;
  const preference = prompt("修改偏好", user.travel_preference || "");
  if (preference === null) return;
  const params = new URLSearchParams({ user_id: userId, nickname, city_name: city, travel_preference: preference });
  state.adminUsers = await fetchJson(`/api/admin/update-user?${params.toString()}`);
  await loadAdminUsers();
}

async function deleteAdminUser(userId) {
  if (!confirm("确认删除这个游客账号及其收藏、评论记录吗")) return;
  state.adminUsers = await fetchJson(`/api/admin/delete-user?user_id=${encodeURIComponent(userId)}`);
  await loadAdminUsers();
  await renderPortrait(true);
}

async function loadAdminComments() {
  if (!$("adminCommentBody")) return;
  const rows = await fetchJson("/api/admin/comments").catch(() => []);
  $("adminCommentBody").innerHTML = rows.length ? rows.slice(0, 40).map((row) => `
    <tr>
      <td>${html(row.created_at || "-")}</td>
      <td>${html(row.nickname || row.username || "-")}<br><span class="muted-small">${row.role === "operator" ? "管理员" : "游客"}</span></td>
      <td>${html(row.poi_name || "-")}</td>
      <td>${row.parent_id ? "<span class='reply-badge'>回复</span>" : ""}${html(row.content || "")}</td>
      <td><button class="mini-button" data-admin-reply="${row.id}" data-poi="${row.poi_id}" data-name="${html(row.poi_name || "")}" data-city="${html(row.city_name || "")}">回复</button></td>
    </tr>
  `).join("") : `<tr><td colspan="5">暂无评论</td></tr>`;
  document.querySelectorAll("[data-admin-reply]").forEach((btn) => btn.addEventListener("click", () => openCommentModal({
    poi_id: btn.dataset.poi,
    poi_name: btn.dataset.name,
    city_name: btn.dataset.city,
    parent_id: btn.dataset.adminReply,
  })));
}

async function buildAiAssistant() {
  state.guideOptions = await fetchJson("/api/guide-options");
  const cities = state.guideOptions.cities || [];
  $("aiCityOptions").innerHTML = cities.map((x) => `<option value="${html(x)}"></option>`).join("");
  $("aiPreferenceSelector").innerHTML = (state.guideOptions.preferences || []).map((x) => `<option>${html(x)}</option>`).join("");
  $("aiThemeSelector").innerHTML = (state.guideOptions.themes || []).map((x) => `<option>${html(x)}</option>`).join("");
  if (cities.includes("上海市")) $("aiCityInput").value = "上海市";
  if ((state.guideOptions.preferences || []).includes("特种兵")) $("aiPreferenceSelector").value = "轻松舒适";
  $("aiBudgetInput").value = "2000";
  $("aiCityInput").addEventListener("blur", () => {
    const value = resolveAiCity($("aiCityInput").value);
    if (value) $("aiCityInput").value = value;
  });
  $("aiGenerateButton").addEventListener("click", () => loadAiPlan(true));
  $("aiImportPlanButton")?.addEventListener("click", () => importLatestAiPlan().catch((e) => alert(e.message)));
  await loadAmapScript();
  await loadAiPlan(false);
}

function resolveAiCity(input) {
  const value = String(input || "").trim();
  const cities = state.guideOptions?.cities || [];
  if (!value) return cities.includes("上海市") ? "上海市" : (cities[0] || "");
  if (cities.includes(value)) return value;
  const found = cities.find((city) => city.includes(value) || value.includes(city));
  return found || value;
}

async function loadAiPlan(useLlm = true) {
  const city = resolveAiCity($("aiCityInput").value);
  if (city) $("aiCityInput").value = city;
  const params = new URLSearchParams({
    city,
    days: $("aiDaysSelector").value,
    preference: $("aiPreferenceSelector").value,
    theme: $("aiThemeSelector").value,
    budget: $("aiBudgetInput").value || "0",
    use_llm: useLlm ? "1" : "0",
  });
  if (useLlm) $("aiPlanResult").innerHTML = "<h3>正在生成攻略</h3><p>正在结合景点数据、预算和偏好生成路线，请稍候</p>";
  const data = await fetchJson(`/api/guide-plan?${params.toString()}`);
  state.latestAiPlan = data;
  renderAiPlan(data);
  if (state.currentUser?.role === "tourist") renderPlans();
}

function splitLlmAnswer(answer) {
  const text = String(answer || "").replace(/\n{2,}/g, "\n").trim();
  if (!text) return [];
  const sections = [
    ["路线安排", ["路线", "每日", "·", "第一天", "行程"]],
    ["食宿安排", ["早餐", "美食", "住宿", "酒店"]],
    ["交通安全", ["交通", "地铁", "公交", "打车", "换乘"]],
    ["出行提醒", ["提醒", "避坑", "天气", "预约", "注意"]],
  ];
  return sections.map(([name, keys]) => {
    const lines = text.split("\n").filter((line) => keys.some((key) => line.includes(key))).slice(0, 4);
    return { name, content: lines.length ? lines.join("\n") : text.slice(0, 180) };
  });
}

function renderLlmTable(data) {
  const rows = data.llm_answer ? splitLlmAnswer(data.llm_answer) : [
    { name: "路线安排", content: "根据左侧地图顺序串联景点，优先选择距离近、主题一致的路线" },
    { name: "食宿安排", content: "住宿建议选择核心商圈或交通枢纽附近，餐饮优先结合当地特色街区" },
    { name: "交通安全", content: "城市内优先地铁、公交和短途打车组合，跨区景点预留换乘时间" },
    { name: "出行提醒", content: "热门景点提前预约，雨天减少户外停留，节假日尽量错峰" },
  ];
  $("aiLlmTable").innerHTML = `
    <h3>大模型重点建议</h3>
    <div class="llm-highlight-grid">
      ${rows.map((row, index) => `
        <section>
          <span>0${index + 1}</span>
          <strong>${html(row.name)}</strong>
          <p>${html(row.content)}</p>
        </section>
      `).join("")}
    </div>
  `;
}

function renderAiPlan(data) {
  const pois = data.pois || [];
  const plan = data.local_plan || {};
  $("aiPlanResult").innerHTML = `
    <h3>${html(plan.title || "旅行方案")}</h3>
    <p>${html(plan.summary || "")}</p>
    <div class="compact-plan">
      ${(plan.days || []).map((day) => `<p><strong>强>${day.day} 天：${html(day.theme)}</strong><br>${html((day.route || []).filter(Boolean).join(" →") || "根据实际交通灵活安排")}</p>`).join("")}
    </div>
    <ul class="tip-list">${(plan.tips || []).map((tip) => `<li>${html(tip)}</li>`).join("")}</ul>
  `;
  renderLlmTable(data);
  $("aiPoiList").innerHTML = scenicCards(pois, 8);
  bindCardActions($("aiPoiList"));
  renderAiMap(pois);
}

function orderRoutePoints(points) {
  const source = points.filter((x) => x.longitude && x.latitude).slice(0, 12);
  if (source.length <= 2) return source;
  const ordered = [source.slice().sort((a, b) => Number(b.heat_score || 0) - Number(a.heat_score || 0))[0]];
  const rest = source.filter((x) => x !== ordered[0]);
  const distance = (a, b) => Math.hypot(Number(a.longitude) - Number(b.longitude), Number(a.latitude) - Number(b.latitude));
  while (rest.length) {
    const last = ordered[ordered.length - 1];
    rest.sort((a, b) => distance(last, a) - distance(last, b));
    ordered.push(rest.shift());
  }
  return ordered;
}

function renderAiMap(pois) {
  if (state.config.amap_key && window.AMap) {
    renderAmap(pois);
    return;
  }
  const chart = state.charts.aiMapBox;
  if (!chart) return;
  $("mapStatus").textContent = state.config.amap_key ? "高德脚本加载中，暂用坐标图展示" : "未配置高德 Key，使用内置坐标图展示";
  const rows = orderRoutePoints(pois.filter((x) => x.longitude && x.latitude));
  chart.setOption({
    ...baseChart(),
    tooltip: { formatter: (p) => `${html(p.data.name)}<br>${html(p.data.city)}<br>热度：{dec(p.data.heat, 1)}` },
    grid: { left: 52, right: 22, top: 16, bottom: 44 },
    xAxis: { type: "value", name: "经度", min: 113, max: 123 },
    yAxis: { type: "value", name: "纬度", min: 23, max: 38 },
    dataZoom: [{ type: "inside", xAxisIndex: 0 }, { type: "inside", yAxisIndex: 0 }, { type: "slider", xAxisIndex: 0, bottom: 8 }, { type: "slider", yAxisIndex: 0, right: 4 }],
    series: [{ type: "scatter", data: rows.map((row, index) => ({ name: row.poi_name, city: row.city_name, heat: row.heat_score, value: [row.longitude, row.latitude, row.heat_score || 1], order: index + 1 })), symbolSize: (v) => Math.max(16, Math.min(38, Number(v[2]) * 5)), itemStyle: { color: palette.red, opacity: 0.86 }, label: { show: true, formatter: (p) => `${p.data.order}. ${p.data.name}`, position: "right", fontSize: 11 } }],
  });
}

function loadAmapScript() {
  if (!state.config.amap_key || window.AMap) return Promise.resolve();
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(state.config.amap_key)}&plugin=AMap.Scale,AMap.ToolBar`;
    script.onload = resolve;
    script.onerror = resolve;
    document.head.appendChild(script);
  });
}

function loadBaiduPanoramaScript() {
  if (!state.config.baidu_ak || window.BMapGL) return Promise.resolve();
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = `https://api.map.baidu.com/api?type=webgl&v=1.0&ak=${encodeURIComponent(state.config.baidu_ak)}&services=1`;
    script.onload = resolve;
    script.onerror = resolve;
    document.head.appendChild(script);
  });
}

function gcj02ToBd09(lng, lat) {
  const x = Number(lng);
  const y = Number(lat);
  const z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * Math.PI * 3000.0 / 180.0);
  const theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * Math.PI * 3000.0 / 180.0);
  return {
    lng: z * Math.cos(theta) + 0.0065,
    lat: z * Math.sin(theta) + 0.006,
  };
}

async function renderBaiduPanorama(box, payload) {
  if (!state.config.baidu_ak) return false;
  await loadBaiduPanoramaScript();
  if (!window.BMapGL) return false;
  const bdPoint = gcj02ToBd09(payload.longitude, payload.latitude);
  return new Promise((resolve) => {
    try {
      const point = new BMapGL.Point(bdPoint.lng, bdPoint.lat);
      const service = new BMapGL.PanoramaService();
      service.getPanoramaByLocation(point, (data) => {
        if (!data || !data.id) {
          resolve(false);
          return;
        }
        box.innerHTML = "";
        state.previewMap = new BMapGL.Panorama("previewMapBox");
        state.previewMap.setPosition(point);
        if (typeof state.previewMap.setPov === "function") state.previewMap.setPov({ heading: 0, pitch: 0 });
        resolve(true);
      });
    } catch (error) {
      console.warn("preview baidu panorama failed", error);
      resolve(false);
    }
  });
}

function renderAmap(pois) {
  const el = $("aiMapBox");
  if (state.charts.aiMapBox) {
    state.charts.aiMapBox.dispose();
    state.charts.aiMapBox = null;
  }
  el.innerHTML = "";
  const first = pois.find((x) => x.longitude && x.latitude);
  state.amap = new AMap.Map("aiMapBox", {
    zoom: 8,
    center: first ? [first.longitude, first.latitude] : [120.16, 30.25],
    dragEnable: true,
    scrollWheel: true,
    zoomEnable: true,
  });
  try {
    state.amap.addControl(new AMap.Scale());
    state.amap.addControl(new AMap.ToolBar());
  } catch {}
  const points = orderRoutePoints(pois.filter((x) => x.longitude && x.latitude)).slice(0, 12);
  points.forEach((poi, index) => {
    const marker = new AMap.Marker({
      position: [poi.longitude, poi.latitude],
      title: poi.poi_name,
      content: `<div class="amap-order-marker">${index + 1}</div>`,
      offset: new AMap.Pixel(-15, -15),
    });
    const info = new AMap.InfoWindow({
      content: `<div style="padding:6px 4px;line-height:1.7"><strong>${index + 1}. ${html(poi.poi_name)}</strong><br>${html(poi.city_name || "")}<br>热度：{dec(poi.heat_score, 1)}　评分：{dec(poi.comment_score, 1)}</div>`,
      offset: new AMap.Pixel(0, -28),
    });
    marker.on("click", () => info.open(state.amap, marker.getPosition()));
    marker.setMap(state.amap);
  });
  const routePoints = points.slice(0, 8).map((poi) => [poi.longitude, poi.latitude]);
  if (routePoints.length >= 2) {
    const polyline = new AMap.Polyline({
      path: routePoints,
      strokeColor: "#c65d3b",
      strokeWeight: 5,
      strokeOpacity: 0.82,
      lineJoin: "round",
    });
    state.amap.add(polyline);
    state.amap.setFitView([polyline]);
  } else if (points.length) {
    state.amap.setFitView();
  }
  $("mapStatus").textContent = "已接入高德地图，可拖动缩放；路线按热度起点和就近顺序生成";
}





function currentPlanMeta() {
  if (state.currentPlanDetail?.plan) return state.currentPlanDetail.plan;
  return state.plans.find((row) => Number(row.id) === Number(state.activePlanId)) || null;
}

function currentPlanDayCount() {
  const plan = currentPlanMeta();
  return Math.max(1, Number(plan?.total_days || state.currentPlanDetail?.days?.length || 1));
}

function planDateText(plan) {
  if (!plan) return "-";
  const start = String(plan.start_date || "").slice(0, 10);
  const end = String(plan.end_date || "").slice(0, 10);
  if (start && end) return `${start} \u81f3 ${end}`;
  return start || end || "\u672a\u8bbe\u7f6e\u65e5\u671f";
}

function planBudgetText(plan) {
  const value = Number(plan?.budget || 0);
  return value > 0 ? `\u00a5${fmt(value)}` : "\u672a\u8bbe\u7f6e\u9884\u7b97";
}

function planTypeMeta(type) {
  const source = String(type || "").trim();
  const value = source.toLowerCase();
  if (["\u666f\u70b9", "scenic", "poi"].includes(value)) return { label: "\u666f\u70b9", className: "type-scenic" };
  if (["\u9910\u996e", "meal", "food"].includes(value)) return { label: "\u9910\u996e", className: "type-meal" };
  if (["\u4ea4\u901a", "transport", "trip"].includes(value)) return { label: "\u4ea4\u901a", className: "type-transport" };
  if (["\u4f4f\u5bbf", "hotel", "stay"].includes(value)) return { label: "\u4f4f\u5bbf", className: "type-hotel" };
  return { label: source || "\u6d3b\u52a8", className: "type-activity" };
}

function closePlanFab() {
  $("planFabMenu")?.classList.add("hidden");
  $("planFab")?.classList.remove("open");
}

function togglePlanFab() {
  $("planFabMenu")?.classList.toggle("hidden");
  $("planFab")?.classList.toggle("open");
}

function closePlanEditorModal() {
  const modal = $("planEditorModal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.innerHTML = "";
}

function openPlanEditorModal(markup) {
  const modal = $("planEditorModal");
  if (!modal) return;
  modal.innerHTML = markup;
  modal.classList.remove("hidden");
  $("planEditorClose")?.addEventListener("click", closePlanEditorModal);
}

function emptyPlanMarkup(title, text) {
  return `<div class="plan-empty-card"><strong>${html(title)}</strong><p>${html(text)}</p></div>`;
}

async function loadPlans(preferredPlanId = 0) {
  if (!state.currentUser || state.currentUser.role !== "tourist") {
    state.plans = [];
    state.activePlanId = 0;
    state.currentPlanDetail = null;
    renderPlans();
    return;
  }
  const rows = await fetchJson(`/api/user/plans?user_id=${state.currentUser.id}`);
  state.plans = rows || [];
  if (!state.plans.length) {
    state.activePlanId = 0;
    state.currentPlanDetail = null;
    renderPlans();
    return;
  }
  const targetId = Number(preferredPlanId || state.activePlanId || state.plans[0].id || 0);
  const targetPlan = state.plans.find((row) => Number(row.id) === Number(targetId)) || state.plans[0];
  await loadPlanDetail(targetPlan.id);
}

async function loadPlanDetail(planId) {
  const numericId = Number(planId || 0);
  if (!state.currentUser || !numericId) {
    state.activePlanId = 0;
    state.currentPlanDetail = null;
    renderPlans();
    return;
  }
  const data = await fetchJson(`/api/user/plan-detail?user_id=${state.currentUser.id}&plan_id=${numericId}`);
  state.activePlanId = Number(data?.plan?.id || numericId);
  state.currentPlanDetail = data;
  renderPlans();
}

function renderPlanSelector() {
  const selector = $("planSelector");
  if (!selector) return;
  if (!state.plans.length) {
    selector.innerHTML = `<option value="">\u6682\u65e0\u65c5\u884c\u8ba1\u5212</option>`;
    selector.disabled = true;
    return;
  }
  selector.disabled = false;
  selector.innerHTML = state.plans.map((row) => `
    <option value="${row.id}" ${Number(row.id) === Number(state.activePlanId) ? "selected" : ""}>
      ${html(row.title || row.destination || `\u8ba1\u5212 ${row.id}`)}
    </option>
  `).join("");
}

function renderPlanSummaryCards() {
  const root = $("planSummaryCards");
  if (!root) return;
  const plan = currentPlanMeta();
  const detail = state.currentPlanDetail || {};
  const itemCount = (detail.items || []).length;
  if (!plan) {
    root.innerHTML = [
      ["\u8ba1\u5212\u603b\u6570", 0],
      ["\u5f53\u524d\u76ee\u7684\u5730", "-"],
      ["\u884c\u7a0b\u5929\u6570", 0],
      ["\u884c\u7a0b\u6761\u76ee", 0],
    ].map(([label, value]) => `<span><strong>${html(String(value))}</strong>${html(label)}</span>`).join("");
    return;
  }
  root.innerHTML = [
    ["\u8ba1\u5212\u603b\u6570", state.plans.length],
    ["\u5f53\u524d\u76ee\u7684\u5730", plan.destination || "-"],
    ["\u884c\u7a0b\u5929\u6570", plan.total_days || currentPlanDayCount()],
    ["\u884c\u7a0b\u6761\u76ee", itemCount],
  ].map(([label, value]) => `<span><strong>${html(String(value))}</strong>${html(label)}</span>`).join("");
}

function renderPlanList() {
  const root = $("planList");
  if (!root) return;
  if (!state.plans.length) {
    root.innerHTML = emptyPlanMarkup("\u8fd8\u6ca1\u6709\u65c5\u884c\u8ba1\u5212", "\u53ef\u4ee5\u5148\u624b\u52a8\u65b0\u5efa\uff0c\u4e5f\u53ef\u4ee5\u5148\u53bb AI \u667a\u80fd\u52a9\u624b\u751f\u6210\uff0c\u518d\u4e00\u952e\u5bfc\u5165\u5230\u5f53\u524d\u8ba1\u5212\u3002");
    return;
  }
  root.innerHTML = state.plans.map((plan) => `
    <article class="plan-list-card ${Number(plan.id) === Number(state.activePlanId) ? "active" : ""}" data-plan-switch="${plan.id}">
      <strong>${html(plan.title || plan.destination || `\u8ba1\u5212 ${plan.id}`)}</strong>
      <p>${html(plan.destination || "\u672a\u586b\u5199\u76ee\u7684\u5730")}</p>
      <div class="plan-list-meta">
        <span>${html(planDateText(plan))}</span>
        <span>${html(planBudgetText(plan))}</span>
      </div>
      <div class="plan-list-meta">
        <span>${fmt(plan.total_days || 0)} \u5929</span>
        <span>${fmt(plan.item_count || 0)} \u6761\u5b89\u6392</span>
      </div>
    </article>
  `).join("");
  root.querySelectorAll("[data-plan-switch]").forEach((node) => {
    node.addEventListener("click", () => loadPlanDetail(node.dataset.planSwitch).catch((e) => alert(e.message)));
  });
}

function renderPlanOverview() {
  const root = $("planOverviewBox");
  if (!root) return;
  const plan = currentPlanMeta();
  const detail = state.currentPlanDetail || {};
  if (!plan) {
    root.innerHTML = `
      <h3>\u8ba1\u5212\u6982\u89c8</h3>
      <p>\u8fd9\u91cc\u4f1a\u5c55\u793a\u5f53\u524d\u8ba1\u5212\u7684\u65f6\u95f4\u3001\u9884\u7b97\u3001AI \u5bfc\u5165\u72b6\u6001\u548c\u6574\u4f53\u8bf4\u660e\u3002</p>
      ${emptyPlanMarkup("\u5f53\u524d\u6ca1\u6709\u9009\u4e2d\u7684\u8ba1\u5212", "\u70b9\u51fb\u53f3\u4e0b\u89d2\u60ac\u6d6e\u6309\u94ae\u5373\u53ef\u65b0\u5efa\u8ba1\u5212\uff0c\u6216\u8005\u5148\u53bb AI \u667a\u80fd\u52a9\u624b\u751f\u6210\u65b9\u6848\u540e\u518d\u5bfc\u5165\u3002")}
    `;
    return;
  }
  const aiStatus = state.latestAiPlan?.local_plan?.days?.length
    ? `\u5df2\u751f\u6210 ${state.latestAiPlan.local_plan.days.length} \u5929 AI \u884c\u7a0b\uff0c\u53ef\u8ffd\u52a0\u5bfc\u5165`
    : "\u6682\u672a\u751f\u6210\u65b0\u7684 AI \u884c\u7a0b";
  root.innerHTML = `
    <div class="plan-overview-card-head">
      <div>
        <h3>${html(plan.title || "\u65c5\u884c\u8ba1\u5212")}</h3>
        <p>${html(plan.destination || "\u672a\u586b\u5199\u76ee\u7684\u5730")}</p>
      </div>
      <div class="plan-inline-actions">
        <button class="ghost-button small-button" id="planOverviewEdit">\u7f16\u8f91\u8ba1\u5212</button>
        <button class="ghost-button small-button" id="planOverviewDelete">\u5220\u9664\u8ba1\u5212</button>
      </div>
    </div>
    <div class="plan-overview-meta">
      <span><b>\u65f6\u95f4</b>${html(planDateText(plan))}</span>
      <span><b>\u9884\u7b97</b>${html(planBudgetText(plan))}</span>
      <span><b>\u5929\u6570</b>${fmt(plan.total_days || currentPlanDayCount())} \u5929</span>
      <span><b>AI \u72b6\u6001</b>${html(aiStatus)}</span>
    </div>
    <p class="plan-overview-copy">${html(plan.note || "\u652f\u6301 AI \u751f\u6210 + \u624b\u52a8\u8865\u5145 + \u4e00\u952e\u5bfc\u5165\uff0c\u9002\u5408\u5148\u7c97\u6392\u8def\u7ebf\uff0c\u518d\u9010\u5929\u7ec6\u5316\u884c\u7a0b\u3002")}</p>
    <div class="plan-overview-pills">
      <span class="budget-chip">\u5f53\u524d\u5171 ${fmt((detail.items || []).length)} \u6761\u884c\u7a0b</span>
      <span class="budget-chip">\u65b0\u589e\u5185\u5bb9\u4f1a\u81ea\u52a8\u6309\u65f6\u95f4\u6392\u5e8f</span>
      <span class="budget-chip">AI \u5bfc\u5165\u9ed8\u8ba4\u8ffd\u52a0\uff0c\u4e0d\u8986\u76d6\u5df2\u6709\u5185\u5bb9</span>
    </div>
  `;
  $("planOverviewEdit")?.addEventListener("click", () => openPlanFormModal("edit"));
  $("planOverviewDelete")?.addEventListener("click", () => deleteCurrentPlan().catch((e) => alert(e.message)));
}

function renderPlanDayBoard() {
  const root = $("planDayBoard");
  const dayHint = $("planDayHint");
  if (!root) return;
  const detail = state.currentPlanDetail || {};
  const plan = currentPlanMeta();
  if (!plan || !detail.days?.length) {
    root.innerHTML = emptyPlanMarkup("\u8fd8\u6ca1\u6709\u9010\u5929\u884c\u7a0b", "\u53ef\u4ee5\u5148\u624b\u52a8\u65b0\u589e\u884c\u7a0b\uff0c\u6216\u8005\u901a\u8fc7 AI \u667a\u80fd\u52a9\u624b\u751f\u6210\u540e\uff0c\u4e00\u952e\u8ffd\u52a0\u5230\u5f53\u524d\u8ba1\u5212\u3002");
    if (dayHint) dayHint.textContent = "\u6309\u5929\u67e5\u770b\u540e\uff0c\u53ef\u7ee7\u7eed\u7ec6\u5316\u6bcf\u4e00\u6761\u5b89\u6392";
    return;
  }
  if (dayHint) {
    dayHint.textContent = state.planQuickEdit
      ? "\u5f53\u524d\u4e3a\u5feb\u901f\u7f16\u8f91\u6a21\u5f0f\uff0c\u53ef\u76f4\u63a5\u6539\u52a8\u6216\u5220\u9664\u884c\u7a0b\u9879"
      : "\u5f53\u524d\u4e3a\u6d4f\u89c8\u6a21\u5f0f\uff0c\u53ef\u6309\u5929\u67e5\u770b\uff0c\u4e5f\u53ef\u70b9\u51fb\u53f3\u4e0b\u89d2\u7ee7\u7eed\u65b0\u589e";
  }
  root.innerHTML = detail.days.map((day) => `
    <section class="plan-day-column">
      <div class="plan-day-column-head">
        <div>
          <strong>Day ${day.day_no}</strong>
          <span>${html(plan.destination || "\u5f53\u524d\u884c\u7a0b")} \u00b7 ${fmt((day.items || []).length)} \u6761\u5b89\u6392</span>
        </div>
        <button class="mini-button" data-day-add="${day.day_no}">\u65b0\u589e\u884c\u7a0b</button>
      </div>
      <div class="plan-item-stack">
        ${(day.items || []).length ? day.items.map((item) => {
          const meta = planTypeMeta(item.item_type);
          return `
            <article class="plan-item-card">
              <div class="plan-item-top">
                <span class="plan-item-time">${html(item.item_time || "09:00")}</span>
                <span class="plan-item-type ${meta.className}">${html(meta.label)}</span>
              </div>
              <strong>${html(item.title || "\u672a\u547d\u540d\u884c\u7a0b")}</strong>
              <p>${html(item.location || "\u672a\u586b\u5199\u5730\u70b9")}</p>
              <div class="plan-item-note">${html(item.note || "\u6682\u65e0\u5907\u6ce8")}</div>
              <div class="plan-item-source">\u6765\u6e90\uff1a${html(item.source === "ai" ? "AI \u5bfc\u5165" : "\u624b\u52a8\u7f16\u8f91")}</div>
              ${state.planQuickEdit ? `
                <div class="plan-item-actions">
                  <button class="mini-button" data-plan-item-edit="${item.id}">\u7f16\u8f91</button>
                  <button class="mini-button danger" data-plan-item-delete="${item.id}">\u5220\u9664</button>
                </div>
              ` : ""}
            </article>
          `;
        }).join("") : `<div class="plan-day-empty">\u5f53\u5929\u8fd8\u6ca1\u6709\u5b89\u6392\u5185\u5bb9\uff0c\u53ef\u4ee5\u624b\u52a8\u6dfb\u52a0\uff0c\u4e5f\u53ef\u4ee5\u628a AI \u884c\u7a0b\u8ffd\u52a0\u8fdb\u6765\u3002</div>`}
      </div>
    </section>
  `).join("");
  root.querySelectorAll("[data-day-add]").forEach((btn) => {
    btn.addEventListener("click", () => openPlanItemModal({ day_no: btn.dataset.dayAdd }));
  });
  root.querySelectorAll("[data-plan-item-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = (detail.items || []).find((row) => Number(row.id) === Number(btn.dataset.planItemEdit));
      openPlanItemModal(item || {});
    });
  });
  root.querySelectorAll("[data-plan-item-delete]").forEach((btn) => {
    btn.addEventListener("click", () => deletePlanItem(btn.dataset.planItemDelete).catch((e) => alert(e.message)));
  });
}

function renderPlans() {
  renderPlanSelector();
  renderPlanSummaryCards();
  renderPlanList();
  renderPlanOverview();
  renderPlanDayBoard();
  const hint = $("planCurrentHint");
  if (hint) {
    hint.textContent = state.latestAiPlan?.local_plan?.days?.length
      ? `\u6700\u8fd1\u5df2\u751f\u6210 ${state.latestAiPlan.local_plan.days.length} \u5929 AI \u884c\u7a0b\uff0c\u53ef\u4e00\u952e\u8ffd\u52a0\u5230\u5f53\u524d\u8ba1\u5212`
      : "\u5148\u5728 AI \u667a\u80fd\u52a9\u624b\u751f\u6210\u884c\u7a0b\uff0c\u518d\u56de\u5230\u8fd9\u91cc\u4e00\u952e\u5bfc\u5165";
  }
  const fabQuick = $("planFabQuickEdit");
  if (fabQuick) fabQuick.textContent = state.planQuickEdit ? "\u5173\u95ed\u5feb\u901f\u7f16\u8f91" : "\u5f00\u542f\u5feb\u901f\u7f16\u8f91";
}

function openPlanFormModal(mode = "create") {
  const plan = mode === "edit" ? currentPlanMeta() : null;
  closePlanFab();
  openPlanEditorModal(`
    <div class="comment-panel plan-editor-panel">
      <div class="drawer-head">
        <div><p class="eyebrow">PLAN</p><h2>${mode === "edit" ? "\u7f16\u8f91\u65c5\u884c\u8ba1\u5212" : "\u65b0\u5efa\u65c5\u884c\u8ba1\u5212"}</h2></div>
        <button class="icon-button" id="planEditorClose">&times;</button>
      </div>
      <div class="form-grid plan-form-grid">
        <label>\u8ba1\u5212\u540d\u79f0 <input id="planFormTitle" value="${html(plan?.title || "")}" placeholder="\u4f8b\u5982 \u4e0a\u6d77 3 \u65e5\u8f7b\u677e\u6e38" /></label>
        <label>\u76ee\u7684\u5730 <input id="planFormDestination" value="${html(plan?.destination || "")}" placeholder="\u4f8b\u5982 \u4e0a\u6d77\u5e02" /></label>
        <label>\u5f00\u59cb\u65e5\u671f <input id="planFormStart" type="date" value="${html(String(plan?.start_date || "").slice(0, 10))}" /></label>
        <label>\u7ed3\u675f\u65e5\u671f <input id="planFormEnd" type="date" value="${html(String(plan?.end_date || "").slice(0, 10))}" /></label>
        <label>\u9884\u7b97 <input id="planFormBudget" type="number" min="0" step="100" value="${html(String(Math.round(Number(plan?.budget || 0)) || ""))}" placeholder="\u4f8b\u5982 2000" /></label>
        <label class="wide-field">\u5907\u6ce8 <textarea id="planFormNote" placeholder="\u53ef\u5199\u4e0b\u8fd9\u6b21\u51fa\u884c\u7684\u4e3b\u9898\u3001\u540c\u884c\u4eba\u3001\u8282\u594f\u8981\u6c42\u7b49">${html(plan?.note || "")}</textarea></label>
      </div>
      <button class="primary-button full" id="planFormSubmit">\u4fdd\u5b58\u8ba1\u5212</button>
    </div>
  `);
  $("planFormSubmit")?.addEventListener("click", async () => {
    const payload = {
      user_id: state.currentUser?.id,
      plan_id: mode === "edit" ? plan?.id : 0,
      title: $("planFormTitle").value.trim(),
      destination: $("planFormDestination").value.trim(),
      start_date: $("planFormStart").value,
      end_date: $("planFormEnd").value,
      budget: $("planFormBudget").value,
      note: $("planFormNote").value.trim(),
    };
    const data = await fetchJsonPost("/api/user/plan/save-json", payload);
    closePlanEditorModal();
    await loadPlans(data?.plan?.id || data?.id || payload.plan_id);
  });
}

function openPlanItemModal(item = {}) {
  const plan = currentPlanMeta();
  if (!plan) {
    alert("\u8bf7\u5148\u521b\u5efa\u4e00\u4e2a\u65c5\u884c\u8ba1\u5212");
    return;
  }
  closePlanFab();
  const dayCount = currentPlanDayCount();
  const selectedDay = Number(item.day_no || 1);
  const currentType = planTypeMeta(item.item_type).label;
  const typeOptions = ["\u666f\u70b9", "\u9910\u996e", "\u4ea4\u901a", "\u4f4f\u5bbf", "\u6d3b\u52a8"];
  openPlanEditorModal(`
    <div class="comment-panel plan-editor-panel">
      <div class="drawer-head">
        <div><p class="eyebrow">ITEM</p><h2>${item.id ? "\u7f16\u8f91\u884c\u7a0b\u9879" : "\u65b0\u589e\u884c\u7a0b\u9879"}</h2></div>
        <button class="icon-button" id="planEditorClose">&times;</button>
      </div>
      <div class="form-grid plan-form-grid">
        <label>\u7b2c\u51e0\u5929 <select id="planItemDay">${Array.from({ length: dayCount }, (_, index) => `<option value="${index + 1}" ${index + 1 === selectedDay ? "selected" : ""}>Day ${index + 1}</option>`).join("")}</select></label>
        <label>\u65f6\u95f4 <input id="planItemTime" type="time" value="${html(item.item_time || "09:00")}" /></label>
        <label>\u7c7b\u578b <select id="planItemType">${typeOptions.map((type) => `<option ${currentType === type ? "selected" : ""}>${type}</option>`).join("")}</select></label>
        <label>\u6807\u9898 <input id="planItemTitle" value="${html(item.title || "")}" placeholder="\u4f8b\u5982 \u8c6b\u56ed\u6e38\u89c8" /></label>
        <label>\u5730\u70b9 <input id="planItemLocation" value="${html(item.location || "")}" placeholder="\u4f8b\u5982 \u9ec4\u6d66\u533a\u8c6b\u56ed" /></label>
        <label class="wide-field">\u5907\u6ce8 <textarea id="planItemNote" placeholder="\u53ef\u8865\u5145\u65f6\u957f\u3001\u6ce8\u610f\u4e8b\u9879\u3001\u95e8\u7968\u7b49\u4fe1\u606f">${html(item.note || "")}</textarea></label>
      </div>
      <button class="primary-button full" id="planItemSubmit">\u4fdd\u5b58\u884c\u7a0b\u9879</button>
    </div>
  `);
  $("planItemSubmit")?.addEventListener("click", async () => {
    const payload = {
      user_id: state.currentUser?.id,
      plan_id: state.activePlanId,
      item_id: item.id || 0,
      day_no: $("planItemDay").value,
      item_time: $("planItemTime").value,
      item_type: $("planItemType").value,
      title: $("planItemTitle").value.trim(),
      location: $("planItemLocation").value.trim(),
      note: $("planItemNote").value.trim(),
      source: item.source || "manual",
    };
    const data = await fetchJsonPost("/api/user/plan/item/save-json", payload);
    state.currentPlanDetail = data;
    closePlanEditorModal();
    await loadPlans(state.activePlanId);
  });
}

async function deleteCurrentPlan() {
  const plan = currentPlanMeta();
  if (!plan) return;
  closePlanFab();
  if (!confirm(`\u786e\u5b9a\u5220\u9664\u8ba1\u5212\u201c${plan.title || plan.destination}\u201d\u5417\uff1f`)) return;
  await fetchJsonPost("/api/user/plan/delete-json", { user_id: state.currentUser?.id, plan_id: plan.id });
  await loadPlans();
}

async function deletePlanItem(itemId) {
  if (!state.activePlanId) return;
  if (!confirm("\u786e\u5b9a\u5220\u9664\u8fd9\u6761\u884c\u7a0b\u5417\uff1f")) return;
  const data = await fetchJsonPost("/api/user/plan/item/delete-json", {
    user_id: state.currentUser?.id,
    plan_id: state.activePlanId,
    item_id: itemId,
  });
  state.currentPlanDetail = data;
  renderPlans();
}

function seedAiFromCurrentPlan() {
  const plan = currentPlanMeta();
  if (!plan) return;
  if ($("aiCityInput")) $("aiCityInput").value = plan.destination || "";
  if ($("aiBudgetInput") && Number(plan.budget || 0) > 0) $("aiBudgetInput").value = Math.round(Number(plan.budget || 0));
  const days = currentPlanDayCount();
  if ($("aiDaysSelector")?.querySelector(`option[value="${days}"]`)) $("aiDaysSelector").value = String(days);
}

async function generateAiFromCurrentPlan() {
  seedAiFromCurrentPlan();
  closePlanFab();
  state.activeModule = "ai";
  switchModule();
  await loadAiPlan(true);
}

async function ensurePlanForAiImport() {
  if (state.activePlanId) return state.activePlanId;
  const ai = state.latestAiPlan || {};
  const localPlan = ai.local_plan || {};
  const options = ai.options || {};
  const created = await fetchJsonPost("/api/user/plan/save-json", {
    user_id: state.currentUser?.id,
    title: localPlan.title || `${options.city || "\u65c5\u884c"}${options.days || 1}\u5929\u8ba1\u5212`,
    destination: options.city || localPlan.title || "\u672a\u586b\u5199\u76ee\u7684\u5730",
    start_date: "",
    end_date: "",
    budget: options.budget || localPlan.budget_input || 0,
    note: "\u7531 AI \u65b9\u6848\u81ea\u52a8\u521b\u5efa\uff0c\u53ef\u7ee7\u7eed\u624b\u52a8\u8865\u5145\u3002",
  });
  state.activePlanId = Number(created?.plan?.id || 0);
  return state.activePlanId;
}

async function importLatestAiPlan() {
  if (!state.currentUser) {
    openDrawer();
    return;
  }
  if (!state.latestAiPlan?.local_plan?.days?.length) throw new Error("\u8bf7\u5148\u5728 AI \u667a\u80fd\u52a9\u624b\u4e2d\u751f\u6210\u884c\u7a0b");
  closePlanFab();
  const planId = await ensurePlanForAiImport();
  const data = await fetchJsonPost("/api/user/plan/import-ai-json", {
    user_id: state.currentUser.id,
    plan_id: planId,
    ai_plan: state.latestAiPlan,
  });
  state.currentPlanDetail = data;
  state.activePlanId = Number(data?.plan?.id || planId);
  await loadPlans(state.activePlanId);
  state.activeModule = "plans";
  switchModule();
}

function togglePlanQuickEdit() {
  state.planQuickEdit = !state.planQuickEdit;
  renderPlans();
}

function openDrawer() { $("drawerMask").classList.add("show"); $("profileDrawer").classList.add("show"); }
function closeDrawer() { $("drawerMask").classList.remove("show"); $("profileDrawer").classList.remove("show"); }
function showLogin() { $("loginBox").classList.remove("hidden"); $("registerBox").classList.add("hidden"); $("profileBox").classList.add("hidden"); $("drawerTitle").textContent = "账号登录"; }
function showRegister() { $("loginBox").classList.add("hidden"); $("registerBox").classList.remove("hidden"); $("profileBox").classList.add("hidden"); $("drawerTitle").textContent = "游客注册"; }

function updateProfileUI() {
  const user = state.currentUser;
  if (!user) {
    $("profileName").textContent = "未登录";
    setAvatarPreview(defaultAvatar);
    showLogin();
    return;
  }
  $("loginBox").classList.add("hidden");
  $("registerBox").classList.add("hidden");
  $("profileBox").classList.remove("hidden");
  $("drawerTitle").textContent = "个人中心";
  $("profileName").textContent = user.nickname || user.username;
  setAvatarPreview(avatarOf(user));
  $("drawerName").textContent = user.nickname || user.username;
  $("drawerRole").textContent = user.role === "operator" ? "管理员账号" : "游客账号";
  $("profileNickname").value = user.nickname || "";
  $("profileCity").value = user.city_name || "";
  $("profilePreference").value = user.travel_preference || "";
  if ($("profileAvatarFile")) {
    $("profileAvatarFile").disabled = user.role === "operator";
    $("profileAvatarFile").title = user.role === "operator" ? "管理员头像固定为默认头像" : "";
    $("profileAvatarFile").value = "";
  }
}
async function login() {
  const btn = document.getElementById("loginButton");
  if (!btn) return;
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "登录中...";
  try {
  const username = $("loginUsername").value.trim();
  const password = $("loginPassword").value.trim();
  const data = await fetchJson(`/api/auth/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&role=${state.loginRole}`);
  state.currentUser = data.user;
  state.role = data.user.role === "operator" ? "operator" : "tourist";
  state.activeModule = state.role === "operator" ? "operator" : "home";
  saveSession();
  updateProfileUI();
  showAppAfterAuth();
  await loadFavorites();
  await loadMyComments();
  await loadPlans();
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

async function register() {
  const params = new URLSearchParams({
    username: $("regUsername").value.trim(),
    password: $("regPassword").value.trim(),
    nickname: $("regNickname").value.trim(),
    age: $("regAge").value.trim(),
    city_name: $("regCity").value.trim(),
    travel_preference: $("regPreference").value.trim(),
    budget_level: $("regBudget").value,
  });
  const data = await fetchJson(`/api/auth/register?${params.toString()}`);
  state.currentUser = data.user;
  state.role = "tourist";
  state.activeModule = "home";
  saveSession();
  updateProfileUI();
  showAppAfterAuth();
  await loadFavorites();
  await loadMyComments();
  await loadPlans();
  goDashboardPage();
}

async function saveProfile() {
  if (!state.currentUser) return;
  const payload = {
    user_id: state.currentUser.id,
    nickname: $("profileNickname").value,
    city_name: $("profileCity").value,
    travel_preference: $("profilePreference").value,
  };
  const file = $("profileAvatarFile")?.files?.[0];
  if (file && state.currentUser.role !== "operator") payload.avatar_url = await imageFileToDataUrl(file);
  const res = await fetch("/api/user/update-profile-json", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!body.success) throw new Error(body.message || "保存失败");
  const data = body.data;
  state.currentUser = data.user;
  updateProfileUI();
}

function imageFileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("头像读取失败"));
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        const size = 220;
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        const scale = Math.max(size / img.width, size / img.height);
        const width = img.width * scale;
        const height = img.height * scale;
        ctx.drawImage(img, (size - width) / 2, (size - height) / 2, width, height);
        resolve(canvas.toDataURL("image/jpeg", 0.82));
      };
      img.onerror = () => reject(new Error("头像处理失败"));
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

async function previewAvatarSelection() {
  const file = $("profileAvatarFile")?.files?.[0];
  if (!state.currentUser) return;
  if (!file) {
    updateProfileUI();
    return;
  }
  if (state.currentUser.role === "operator") {
    $("profileAvatarFile").value = "";
    updateProfileUI();
    return;
  }
  const dataUrl = await imageFileToDataUrl(file);
  setAvatarPreview(dataUrl);
}

async function loadFavorites() {
  if (!state.currentUser) return;
  const rows = await fetchJson(`/api/user/favorites?user_id=${state.currentUser.id}`);
  state.favoriteIds = new Set(rows.map((row) => String(row.poi_id)));
  $("favoriteList").innerHTML = rows.length ? rows.slice(0, 20).map((row) => `<article><img src="${html(imageOf(row))}" alt="${html(row.poi_name)}"><div><strong>${html(row.poi_name)}</strong><span>${html(row.city_name || "")}</span></div><button data-remove="${row.poi_id}">移除</button></article>`).join("") : "<p class='hint-text'>暂无收藏，可以去推荐页或筛选页收藏景点</p>";
  document.querySelectorAll("[data-remove]").forEach((btn) => btn.addEventListener("click", async () => { await fetchJson(`/api/user/remove-favorite?user_id=${state.currentUser.id}&poi_id=${btn.dataset.remove}`); await loadFavorites(); refreshFavoriteButtons(); }));
}

async function loadMyComments() {
  if (!state.currentUser) return;
  const rows = await fetchJson(`/api/user/my-comments?user_id=${state.currentUser.id}`);
  $("myCommentList").innerHTML = rows.length ? rows.map((row) => `<article><strong>${html(row.poi_name || "景点")} · ${row.rating} 分</strong><p>${html(row.content || "")}</p><span>${html(row.city_name || "")} · ${html(row.created_at || "")}</span></article>`).join("") : "<p class='hint-text'>暂无评论，可以在景点卡片点击“评论”：//p>";
}

async function openCommentModal(row) {
  if (!state.currentUser) return openDrawer();
  if (!row.poi_id) return;
  state.activeCommentPoi = row;
  state.replyParentId = row.parent_id || "";
  $("commentPoiName").textContent = row.poi_name || "景点评论";
  $("commentContent").value = "";
  $("commentParentId").value = state.replyParentId;
  $("replyHint").textContent = state.replyParentId ? `正在回复评论 #${state.replyParentId}` : "";
  $("commentModal").classList.remove("hidden");
  await loadComments(row.poi_id);
}

async function loadComments(poiId) {
  const rows = await fetchJson(`/api/user/comments?poi_id=${poiId}`);
  $("commentList").innerHTML = rows.length ? rows.map((row) => `
    <article class="${row.parent_id ? "comment-reply" : ""}">
      <strong>${html(row.nickname || "游客")} · ${row.role === "operator" ? "管理员" : "游客"} · ${row.rating} 分</strong>
      <p>${row.parent_id ? `<span class="reply-badge">回复 #${row.parent_id}</span>` : ""}${html(row.content)}</p>
      <span>${html(row.created_at || "")}</span>
      <button class="mini-button" data-reply-comment="${row.id}">回复</button>
    </article>
  `).join("") : "<p class='hint-text'>暂无评论，成为第一个评论的人</p>";
  document.querySelectorAll("[data-reply-comment]").forEach((btn) => btn.addEventListener("click", () => {
    state.replyParentId = btn.dataset.replyComment;
    $("commentParentId").value = state.replyParentId;
    $("replyHint").textContent = `正在回复评论 #${state.replyParentId}`;
    $("commentContent").focus();
  }));
}

async function submitComment() {
  if (!state.currentUser || !state.activeCommentPoi) return;
  const params = new URLSearchParams({
    user_id: state.currentUser.id,
    poi_id: state.activeCommentPoi.poi_id,
    poi_name: state.activeCommentPoi.poi_name || "",
    city_name: state.activeCommentPoi.city_name || "",
    rating: $("commentRating").value,
    content: $("commentContent").value.trim(),
    parent_id: $("commentParentId").value || "",
  });
  await fetchJson(`/api/user/add-comment?${params.toString()}`);
  $("commentParentId").value = "";
  $("replyHint").textContent = "";
  await loadComments(state.activeCommentPoi.poi_id);
  await loadMyComments();
  if (state.role === "operator") await loadAdminComments();
  await renderPortrait(true);
}

function bindUI() {
  document.querySelector(".brand-block")?.addEventListener("click", () => document.querySelector(".side-nav")?.classList.toggle("menu-open"));
  $("touristEntry").addEventListener("click", () => enterApp("tourist"));
  $("operatorEntry").addEventListener("click", () => enterApp("operator"));
  $("goDashboardButton")?.addEventListener("click", goDashboardPage);
  document.querySelectorAll("[data-app-view]").forEach((btn) => btn.addEventListener("click", () => switchAppView(btn.dataset.appView)));
  $("profileButton").addEventListener("click", openDrawer);
  $("drawerClose").addEventListener("click", closeDrawer);
  $("drawerMask").addEventListener("click", closeDrawer);
  $("loginButton").addEventListener("click", () => login().catch((e) => alert(e.message)));
  $("showRegisterButton").addEventListener("click", showRegister);
  $("backLoginButton").addEventListener("click", showLogin);
  $("registerButton").addEventListener("click", () => register().catch((e) => alert(e.message)));
  $("saveProfileButton").addEventListener("click", () => saveProfile().catch((e) => alert(e.message)));
  $("profileAvatarFile")?.addEventListener("change", () => previewAvatarSelection().catch((e) => alert(e.message)));
  $("refreshNewsButton")?.addEventListener("click", () => loadHomeNews().catch((e) => console.warn(e)));
  $("adminCreateUserButton")?.addEventListener("click", () => createAdminUser().catch((e) => alert(e.message)));
  $("logoutButton").addEventListener("click", returnWelcome);
  $("commentClose").addEventListener("click", () => $("commentModal").classList.add("hidden"));
  $("planFabMain")?.addEventListener("click", togglePlanFab);
  $("planFabCreatePlan")?.addEventListener("click", () => openPlanFormModal("create"));
  $("planFabEditPlan")?.addEventListener("click", () => openPlanFormModal("edit"));
  $("planFabDeletePlan")?.addEventListener("click", () => deleteCurrentPlan().catch((e) => alert(e.message)));
  $("planFabAddItem")?.addEventListener("click", () => openPlanItemModal());
  $("planFabGenerateAi")?.addEventListener("click", () => generateAiFromCurrentPlan().catch((e) => alert(e.message)));
  $("planFabImportAi")?.addEventListener("click", () => importLatestAiPlan().catch((e) => alert(e.message)));
  $("planFabQuickEdit")?.addEventListener("click", () => togglePlanQuickEdit());
  $("planSelector")?.addEventListener("change", () => loadPlanDetail($("planSelector").value).catch((e) => alert(e.message)));
  $("planEditorModal")?.addEventListener("click", (event) => { if (event.target?.id === "planEditorModal") closePlanEditorModal(); });
  ensurePreviewModalMarkup();
  $("previewClose")?.addEventListener("click", closePreviewModal);
  $("previewModal")?.addEventListener("click", (event) => {
    if (event.target?.id === "previewModal") closePreviewModal();
  });
  $("submitCommentButton").addEventListener("click", () => submitComment().catch((e) => alert(e.message)));
  document.querySelectorAll(".login-role").forEach((btn) => btn.addEventListener("click", () => {
    state.loginRole = btn.dataset.loginRole;
    document.querySelectorAll(".login-role").forEach((b) => b.classList.toggle("active", b === btn));
    $("loginUsername").value = state.loginRole === "operator" ? "operator" : "tourist";
    $("loginPassword").value = "123456";
    $("showRegisterButton").classList.toggle("hidden", state.loginRole === "operator");
  }));
}

function buildFilterSelectors() {
  const options = state.frontend.filter_panel.options || {};
  const provinces = [...new Set((state.frontend.region_dashboard?.province_summary || []).map((x) => x.province).filter(Boolean))];
  $("filterProvinceSelector").innerHTML = ["全部省份", ...provinces].map((x) => `<option>${html(x)}</option>`).join("");
  $("filterPriceSelector").innerHTML = ["全部价格", ...(options.price_level_options || [])].map((x) => `<option>${html(x)}</option>`).join("");
  $("filterTagSelector").innerHTML = ["全部主题", ...(options.tag_options || []).slice(0, 40)].map((x) => `<option>${html(x)}</option>`).join("");
  rebuildFilterCitySelector();
  $("filterProvinceSelector").addEventListener("change", () => {
    rebuildFilterCitySelector(true);
    updateFilterSearchSuggestions();
    renderFilter();
  });
  ["filterCitySelector", "filterPriceSelector", "filterTagSelector"].forEach((id) => {
    $(id).addEventListener("change", () => {
      updateFilterSearchSuggestions();
      renderFilter();
    });
  });
  $("filterSearchInput").addEventListener("input", () => {
    updateFilterSearchSuggestions();
    renderFilter();
  });
  $("filterSearchInput").addEventListener("change", renderFilter);
  $("filterResetButton")?.addEventListener("click", () => {
    $("filterProvinceSelector").value = "全部省份";
    rebuildFilterCitySelector();
    $("filterPriceSelector").value = "全部价格";
    $("filterTagSelector").value = "全部主题";
    $("filterSearchInput").value = "";
    updateFilterSearchSuggestions();
    renderFilter();
  });
  updateFilterSearchSuggestions();
}

function rebuildFilterCitySelector(focusAfterUpdate = false) {
  const province = $("filterProvinceSelector").value || "全部省份";
  const cityRows = state.frontend.region_dashboard?.city_summary || [];
  const cityOptions = [...new Set(cityRows
    .filter((row) => province === "全部省份" || row.province === province)
    .map((row) => row.city_name)
    .filter(Boolean))];
  const citySelector = $("filterCitySelector");
  const previous = citySelector.value;
  citySelector.innerHTML = ["全部城市", ...cityOptions].map((x) => `<option>${html(x)}</option>`).join("");
  citySelector.value = cityOptions.includes(previous) ? previous : "全部城市";
  if (focusAfterUpdate) citySelector.focus();
}

function searchTextOf(row) {
  return [
    row.poi_name,
    row.city_name,
    row.province,
    row.region_name,
    row.district_name,
    row.tag_text,
    row.short_feature,
    row.reason_text,
  ].join(" ").toLowerCase();
}

function recommendLocationIndex() {
  return state.frontend.recommendation.location_index || {};
}

function recommendProvinces() {
  return recommendLocationIndex().provinces || [];
}

function recommendCities(province = "") {
  const list = recommendLocationIndex().cities_by_province || {};
  return province ? (list[province] || []) : Object.values(list).flat();
}

function recommendPois(province = "", city = "") {
  const list = recommendLocationIndex().pois_by_city || {};
  if (province && city) return list[`${province}||${city}`] || [];
  const all = Object.entries(list).flatMap(([key, items]) => {
    if (province && !key.startsWith(`${province}||`)) return [];
    if (city && !key.endsWith(`||${city}`)) return [];
    return items;
  });
  return all;
}

function recommendMatch(items, keyword, fields) {
  const text = String(keyword || "").trim().toLowerCase();
  if (!text) return items;
  const exact = [];
  const fuzzy = [];
  items.forEach((item) => {
    const blob = fields.map((field) => String(item[field] || "")).join(" ").toLowerCase();
    if (!blob) return;
    if (blob.includes(text)) exact.push(item);
    else if (text.split(/\s+/).some((part) => part && blob.includes(part))) fuzzy.push(item);
  });
  return [...exact, ...fuzzy];
}

function syncRecommendStepbar() {
  const step = $("recommendStepbar");
  if (!step) return;
  step.innerHTML = "";
}

function updateFilterSearchSuggestions() {
  const keyword = String($("filterSearchInput")?.value || "").trim().toLowerCase();
  const province = $("filterProvinceSelector").value || "全部省份";
  const city = $("filterCitySelector").value || "全部城市";
  let rows = (state.frontend.filter_panel.sample_poi || []).filter((row) => (province === "全部省份" || row.province === province) && (city === "全部城市" || row.city_name === city));
  if (keyword) rows = rows.filter((row) => searchTextOf(row).includes(keyword));
  const suggestions = [...new Map(rows.slice(0, 120).map((row) => [row.poi_name, row])).values()].slice(0, 12);
  $("filterSearchSuggestions").innerHTML = suggestions.map((row) => `<option value="${html(row.poi_name || "")}" label="${html(`${row.city_name || ""} ${row.tag_text || ""}`.trim())}"></option>`).join("");
}

function updateRecommendProvinceOptions() {
  const provinces = recommendProvinces();
  $("recommendProvinceOptions").innerHTML = provinces.map((item) => `<option value="${html(item)}"></option>`).join("");
}

function updateRecommendCityOptions() {
  const province = state.recommendProvince || "";
  const cities = fuzzyPick(recommendCities(province), $("recommendCityInput").value, ["city_name", "province"]).slice(0, 18);
  $("recommendCityOptions").innerHTML = cities.map((item) => `<option value="${html(item.city_name)}" label="${html(item.province || "")}"></option>`).join("");
}

function updateRecommendPoiOptions() {
  const province = state.recommendProvince || "";
  const city = state.recommendCity || "";
  const pois = fuzzyPick(recommendPois(province, city), $("recommendPoiInput").value, ["poi_name", "region_name", "tag_text", "short_feature"]).slice(0, 20);
  $("recommendPoiOptions").innerHTML = pois.map((item) => `<option value="${html(item.poi_name)}" label="${html(`${item.city_name || ""} ${item.region_name || ""}`.trim())}"></option>`).join("");
}

function updateRecommendInputsState() {
  const isHybrid = state.recommendAlgorithm === "hybrid";
  $("recommendModeWrap")?.classList.toggle("hidden", !isHybrid);
  $("recommendProvinceWrap")?.classList.toggle("hidden", !isHybrid);
  $("recommendCityWrap")?.classList.toggle("hidden", !isHybrid);
  $("recommendPoiWrap")?.classList.toggle("hidden", !isHybrid);
  $("recommendActionWrap")?.classList.toggle("hidden", false);
  $("recommendCityInput").disabled = !isHybrid || !state.recommendProvince;
  $("recommendPoiInput").disabled = !isHybrid || !state.recommendCity;
  $("recommendAlgorithmSelector").disabled = false;
  syncRecommendStepbar();
}

async function resolveRecommendLocation() {
  const provinceInput = String($("recommendProvinceInput")?.value || "").trim();
  const cityInput = String($("recommendCityInput")?.value || "").trim();
  const poiInput = String($("recommendPoiInput")?.value || "").trim();
  if (!provinceInput) return null;
  const params = new URLSearchParams({
    selected_province: provinceInput,
    selected_city: cityInput,
    city_kw: cityInput,
    poi_kw: poiInput,
    limit: "20",
  });
  const data = await fetchJson(`/api/recommend-locations?${params.toString()}`);
  return {
    province: data.selected_province || provinceInput,
    city: data.selected_city || cityInput || data.cities?.[0]?.city_name || "",
    poi: data.pois?.find((item) => item.poi_name === poiInput)?.poi_name || data.pois?.[0]?.poi_name || poiInput || "",
    cities: data.cities || [],
    pois: data.pois || [],
  };
}

function locationLookup() {
  return state.frontend.recommendation.location_index || {};
}

function locationProvinces() {
  return locationLookup().provinces || [];
}

function locationCities(province = "") {
  const list = locationLookup().cities_by_province || {};
  return province ? (list[province] || []) : Object.values(list).flat();
}

function locationPois(province = "", city = "") {
  const list = locationLookup().pois_by_city || {};
  if (province && city) return list[`${province}||${city}`] || [];
  return Object.entries(list).flatMap(([key, items]) => {
    if (province && !key.startsWith(`${province}||`)) return [];
    if (city && !key.endsWith(`||${city}`)) return [];
    return items;
  }, true);
}

function fuzzyPick(items, keyword, fields) {
  const text = String(keyword || "").trim().toLowerCase();
  if (!text) return items;
  const exact = [];
  const fuzzy = [];
  items.forEach((item) => {
    const blob = fields.map((field) => String(item[field] || "")).join(" ").toLowerCase();
    if (!blob) return;
    if (blob.includes(text)) exact.push(item);
    else if (text.split(/\s+/).some((part) => part && blob.includes(part))) fuzzy.push(item);
  });
  return [...exact, ...fuzzy];
}

function filteredPois() {
  const province = $("filterProvinceSelector").value || "全部省份";
  const city = $("filterCitySelector").value || "全部城市";
  const price = $("filterPriceSelector").value || "全部价格";
  const tag = $("filterTagSelector").value || "全部主题";
  const keyword = String($("filterSearchInput")?.value || "").trim().toLowerCase();
  return (state.frontend.filter_panel.sample_poi || [])
    .filter((row) => (province === "全部省份" || row.province === province)
      && (city === "全部城市" || row.city_name === city)
      && priceMatch(row, price)
      && (tag === "全部主题" || String(row.tag_text || "").includes(tag))
      && (!keyword || searchTextOf(row).includes(keyword)))
    .sort((a, b) => compositeScore(b) - compositeScore(a));
}

function normalizeDistanceLevelFront(value) {
  const text = String(value || "").trim();
  if (!text || /未知|待定|无/.test(text)) return "未知距离";
  if (text.includes("市中心")) return "市中心";
  if (text.includes("近郊")) return "近郊";
  if (text.includes("远郊")) return "远郊";
  return text;
}

function filterSortedPois(rows) {
  const source = rows.slice();
  const mode = state.filterSortMode || "balanced";
  if (mode === "rating") {
    return source.sort((a, b) => Number(b.comment_score || 0) - Number(a.comment_score || 0)
      || Number(b.heat_score || 0) - Number(a.heat_score || 0)
      || Number(b.comment_count || 0) - Number(a.comment_count || 0));
  }
  if (mode === "hot") {
    return source.sort((a, b) => Number(b.heat_score || 0) - Number(a.heat_score || 0)
      || Number(b.comment_count || 0) - Number(a.comment_count || 0)
      || Number(b.comment_score || 0) - Number(a.comment_score || 0));
  }
  if (mode === "review") {
    return source.sort((a, b) => Number(b.comment_count || 0) - Number(a.comment_count || 0)
      || Number(b.comment_score || 0) - Number(a.comment_score || 0)
      || Number(b.heat_score || 0) - Number(a.heat_score || 0));
  }
  if (mode === "budget") {
    return source.sort((a, b) => {
      const freeDiff = Number(a.price || 0) - Number(b.price || 0);
      if (freeDiff !== 0) return freeDiff;
      return Number(b.comment_score || 0) - Number(a.comment_score || 0)
        || Number(b.heat_score || 0) - Number(a.heat_score || 0);
    });
  }
  return source.sort((a, b) => compositeScore(b) - compositeScore(a));
}

function filterTagRows(rows) {
  const counts = {};
  rows.slice(0, 220).forEach((row) => String(row.tag_text || "").split(/[|,，]/).forEach((item) => {
    const tagName = String(item || "").trim();
    if (tagName) counts[tagName] = (counts[tagName] || 0) + 1;
  }));
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([tag_name, poi_count]) => ({ tag_name, poi_count }));
}

function filterPriceRows(rows) {
  const order = ["免费", "1-50元", "51-100元", "100元以上"];
  const counts = { "免费": 0, "1-50元": 0, "51-100元": 0, "100元以上": 0 };
  rows.forEach((row) => {
    const price = Number(row.price || 0);
    if (price <= 0) counts["免费"] += 1;
    else if (price <= 50) counts["1-50元"] += 1;
    else if (price <= 100) counts["51-100元"] += 1;
    else counts["100元以上"] += 1;
  });
  return order.map((price_level) => ({ price_level, poi_count: counts[price_level] })).filter((row) => row.poi_count > 0);
}

function filterDistanceRows(rows) {
  const order = ["市中心", "近郊", "远郊", "未知距离"];
  const counts = { "市中心": 0, "近郊": 0, "远郊": 0, "未知距离": 0 };
  rows.forEach((row) => {
    const label = normalizeDistanceLevelFront(row.distance_level);
    counts[label] = (counts[label] || 0) + 1;
  });
  return order.map((distance_level) => ({ distance_level, poi_count: counts[distance_level] || 0 })).filter((row) => row.poi_count > 0);
}

function filterSummaryMetrics(rows) {
  const total = rows.length;
  const avgScore = total ? rows.reduce((sum, row) => sum + Number(row.comment_score || 0), 0) / total : 0;
  const avgHeat = total ? rows.reduce((sum, row) => sum + Number(row.heat_score || 0), 0) / total : 0;
  const avgPrice = total ? rows.reduce((sum, row) => sum + Number(row.price || 0), 0) / total : 0;
  const freeCount = rows.filter((row) => Number(row.price || 0) <= 0).length;
  return { total, avgScore, avgHeat, avgPrice, freeRatio: total ? freeCount / total : 0 };
}

function uniqueFilterPicks(rows) {
  const picks = [];
  const seen = new Set();
  const push = (title, note, row) => {
    if (!row) return;
    const key = String(row.poi_id || row.poi_name || title);
    if (seen.has(key)) return;
    seen.add(key);
    picks.push({ title, note, row });
  };
  const sortedBalanced = rows.slice().sort((a, b) => compositeScore(b) - compositeScore(a));
  const sortedRating = rows.slice().sort((a, b) => Number(b.comment_score || 0) - Number(a.comment_score || 0));
  const sortedHot = rows.slice().sort((a, b) => Number(b.heat_score || 0) - Number(a.heat_score || 0));
  const sortedBudget = rows.slice().sort((a, b) => Number(a.price || 0) - Number(b.price || 0) || Number(b.comment_score || 0) - Number(a.comment_score || 0));
  push("最值得先看", "综合评分、热度和评论量更平衡", sortedBalanced[0]);
  push("口碑最稳", "更适合优先看评分表现", sortedRating[0]);
  push("热度最高", "更适合热门打卡或跟团决策", sortedHot[0]);
  push("预算友好", "更适合门票敏感型行程", sortedBudget[0]);
  rows.forEach((row) => push("值得纳入备选", "适合继续结合位置和路线判断", row));
  return picks.slice(0, 3);
}

function filterHeroMarkup(rows, sortedRows) {
  const province = $("filterProvinceSelector").value || "全部省份";
  const city = $("filterCitySelector").value || "全部城市";
  const price = $("filterPriceSelector").value || "全部价格";
  const tag = $("filterTagSelector").value || "全部主题";
  const keyword = String($("filterSearchInput")?.value || "").trim();
  const metrics = filterSummaryMetrics(rows);
  const topTags = filterTagRows(rows).slice(0, 3).map((item) => item.tag_name);
  const topRow = sortedRows[0];
  if (!rows.length) {
    return `
      <div>
        <p class="eyebrow">FILTER STUDIO</p>
        <h3>先放宽一点条件，我们再帮你收窄范围</h3>
        <p>当前筛选没有命中景点，比较像是在同时卡住城市、主题和关键词。建议先固定城市，再慢慢加条件。</p>
      </div>
      <div class="filter-query-tags">
        <span>${html(province)}</span>
        <span>${html(city)}</span>
        <span>${html(price)}</span>
        <span>${html(tag)}</span>
        <span>${html(keyword || "无关键词")}</span>
      </div>
    `;
  }
  return `
    <div class="filter-hero-copy">
      <p class="eyebrow">FILTER STUDIO</p>
      <h3>${html(city === "全部城市" ? province : city)} 现在更值得先看的是 ${html(topRow?.poi_name || "这些景点")}</h3>
      <p>这批结果一共筛出 ${fmt(metrics.total)} 个候选景点，平均评分 ${dec(metrics.avgScore, 2)}，平均热度 ${dec(metrics.avgHeat, 1)}。${topTags.length ? `体验重心偏向 ${html(topTags.join(" / "))}。` : ""}</p>
    </div>
    <div class="filter-hero-stats">
      <span><strong>${fmt(metrics.total)}</strong>候选景点</span>
      <span><strong>${metrics.avgPrice > 0 ? `¥${dec(metrics.avgPrice, 0)}` : "免费偏多"}</strong>平均门票</span>
      <span><strong>${pct(metrics.freeRatio)}</strong>免费占比</span>
    </div>
    <div class="filter-query-tags">
      <span>${html(province)}</span>
      <span>${html(city)}</span>
      <span>${html(price)}</span>
      <span>${html(tag)}</span>
      <span>${html(keyword || "无关键词")}</span>
    </div>
  `;
}

function filterPickMarkup(rows) {
  const picks = uniqueFilterPicks(rows);
  return picks.map((item, index) => {
    const row = item.row || {};
    const tags = String(row.tag_text || "").split(/[|,，]/).map((x) => x.trim()).filter(Boolean).slice(0, 2);
    const price = Number(row.price || 0) > 0 ? `¥${dec(row.price, 0)}` : "免费";
    return `
      <article class="filter-pick-card">
        <div class="filter-pick-head">
          <span>0${index + 1}</span>
          <div>
            <strong>${html(item.title)}</strong>
            <p>${html(item.note)}</p>
          </div>
        </div>
        <h4>${html(row.poi_name || "-")}</h4>
        <p>${html(row.city_name || "-")} / ${html(row.region_name || row.district_name || "景区")}</p>
        <div class="filter-pick-meta">
          <span>评分 ${dec(row.comment_score || 0)}</span>
          <span>热度 ${dec(row.heat_score || 0)}</span>
          <span>${html(normalizeDistanceLevelFront(row.distance_level))}</span>
          <span>${price}</span>
        </div>
        ${tags.length ? `<div class="filter-chip-row">${tags.map((tag) => `<span>${html(tag)}</span>`).join("")}</div>` : ""}
      </article>
    `;
  }).join("");
}

function renderFilterResultCards(rows) {
  const box = $("filterPoiList");
  if (!box) return;
  const visible = Math.min(30, rows.length);
  const cardsHtml = scenicCards(rows.slice(0, visible), visible);
  box.classList.remove("large");
  box.innerHTML = cardsHtml;
  bindCardActions(box);
}

function filterResultCards(rows) {
  return rows.slice(0, 10).map((row, index) => {
    const poiId = row.poi_id || row.target_poi_id || "";
    const favored = state.favoriteIds.has(String(poiId));
    const price = Number(row.price || 0) > 0 ? `¥${dec(row.price, 0)}` : "免费";
    const tags = String(row.tag_text || "").split(/[|,，]/).map((x) => x.trim()).filter(Boolean).slice(0, 3);
    const detailUrl = detailOf(row);
    return `
      <article class="filter-poi-card">
        <div class="filter-rank-badge">${index + 1}</div>
        <a class="filter-poi-cover" href="${html(detailUrl)}" target="_blank" rel="noreferrer"><img src="${html(imageOf(row))}" alt="${html(row.poi_name || "景点")}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='${placeholderImage}'"></a>
        <div class="filter-poi-body">
          <div class="filter-poi-topline">
            <div>
              <h4>${html(row.poi_name || "-")}</h4>
              <p>${html(row.city_name || "-")} / ${html(row.region_name || row.district_name || "景区")}</p>
            </div>
            <span class="filter-price-pill">${price}</span>
          </div>
          <p class="filter-poi-desc">${html(row.reason_text || row.short_feature || "适合加入待选清单，继续结合位置和主题比较。")}</p>
          <div class="filter-poi-metrics">
            <span>评分 ${dec(row.comment_score || 0)}</span>
            <span>热度 ${dec(row.heat_score || 0)}</span>
            <span>评论 ${fmt(row.comment_count || 0)}</span>
            <span>${html(normalizeDistanceLevelFront(row.distance_level))}</span>
          </div>
          ${tags.length ? `<div class="filter-chip-row">${tags.map((tag) => `<span>${html(tag)}</span>`).join("")}</div>` : ""}
          <div class="poi-actions">
            <button class="heart-button ${favored ? "active" : ""}" data-fav="${html(poiId)}" data-name="${html(row.poi_name || "")}" data-city="${html(row.city_name || "")}" title="${favored ? "取消收藏" : "收藏"}">${favored ? "❤️" : "♡"}</button>
            <button data-comment="${html(poiId)}" data-name="${html(row.poi_name || "")}" data-city="${html(row.city_name || "")}">评论</button>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

function renderFilter() {
  const rows = filteredPois();
  const province = $("filterProvinceSelector").value || "全部省份";
  const city = $("filterCitySelector").value || "全部城市";
  const price = $("filterPriceSelector").value || "全部价格";
  const tag = $("filterTagSelector").value || "全部主题";
  const keyword = String($("filterSearchInput")?.value || "").trim();
  state.filterVisibleCount = 30;
  $("filterMetricStrip").innerHTML = filterSummary(rows).map((item) => `<span><strong>${html(item.value)}</strong>${html(item.label)}<small>${html(item.extra)}</small></span>`).join("");
  const priceScoreRows = filterPriceScoreRows(rows);
  const tagRows = topTags(rows, 8);
  if (!rows.length) {
    $("filterResultMeta").textContent = "当前条件下没有匹配到景点。可以先放宽城市、主题或关键词，再看分布。";
    setEmptyChart("filterScoreChart", "暂无匹配结果，价格与评分关系无法展示");
    setEmptyChart("filterTagChart", "暂无匹配结果，主题分布无法展示");
    $("filterPoiList").innerHTML = `<div class="plan-empty">没有可展示的景点结果</div>`;
    bindCardActions($("filterPoiList"));
    return;
  }
  setScatter("filterScoreChart", priceScoreRows, (row) => row.priceValue, (row) => row.scoreValue, (row) => row.heatValue * 180, "价格", "评分", palette.green);
  setBar("filterTagChart", tagRows.map((x) => x.tag), tagRows.map((x) => x.count), true, [palette.orange, palette.red]);
  $("filterResultMeta").textContent = `当前匹配 ${fmt(rows.length)} 个景点，下面滚动展示前 30 个符合条件的结果。`;
  renderFilterResultCards(rows);
}

function renderLlmTable(data) {
  const advice = data.llm_advice || {};
  const rows = [
    { name: "路线补充", text: advice.route_note || "", list: advice.highlights || [] },
    { name: "餐饮建议", text: "", list: advice.food_tips || [] },
    { name: "交通建议", text: "", list: advice.transport_tips || [] },
    { name: "出行提醒", text: "", list: advice.tips || [] },
  ];
  $("aiLlmTable").innerHTML = `
    <h3>大模型补充建议</h3>
    <p class="hint-text">结合你当前选择的城市、主题和路线顺序，补充更适合实际出行的建议</p>
    <div class="llm-highlight-grid ai-advice-grid">
      ${rows.map((row, index) => `
        <section>
          <span>0${index + 1}</span>
          <strong>${html(row.name)}</strong>
          ${row.text ? `<p>${html(row.text)}</p>` : ""}
          ${(row.list || []).length
            ? `<ul class="tip-list compact-list">${row.list.map((item) => `<li>${html(item)}</li>`).join("")}</ul>`
            : `<p>暂无额外建议</p>`}
        </section>
      `).join("")}
    </div>
  `;
}

function routePoisOf(data) {
  return (data.route_pois || data.pois || [])
    .filter((row) => row && row.poi_name)
    .sort((a, b) => (Number(a.day || 0) - Number(b.day || 0)) || (Number(a.visit_order || 0) - Number(b.visit_order || 0)));
}

function scheduleTable(day) {
  const rows = day.schedule || [];
  if (!rows.length) return `<div class="plan-empty">当天暂无明确景点安排，可作为自由活动或机动调整时间</div>`;
  return `
    <table class="plan-table">
      <thead><tr><th>时段</th><th>时间</th><th>景点</th><th>地点</th><th>停留</th><th>票价</th></tr></thead>
      <tbody>
        ${rows.map((item) => `
          <tr>
            <td>${html(item.period || "-")}</td>
            <td><span class="plan-time">${html(item.time || "-")}</span></td>
            <td><strong>${html(item.poi_name || "-")}</strong></td>
            <td>${html(item.location || "-")}</td>
            <td>${html(item.stay || "-")}</td>
            <td><span class="plan-price">${html(item.price_text || "-")}</span></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function mealTable(day) {
  const rows = (day.meals && day.meals.length) ? day.meals : [
    { meal_type: "早餐", name: "建议按出发时间在酒店或周边灵活安排", location: "酒店周边", price_text: "自理" },
    { meal_type: "午餐", name: "建议根据当日机动安排就近用餐", location: "景点周边 / 商圈", price_text: "自理" },
    { meal_type: "晚餐", name: "返程日可结合车次或航班在交通枢纽附近就餐", location: "高铁站 / 机场 / 商圈", price_text: "自理" },
  ];
  const hotel = day.hotel || { name: "未匹配到固定酒店", location: "可按预算自行选择", price_text: "待定" };
  return `
    <table class="plan-table">
      <thead><tr><th>餐次 / 住宿</th><th>安排</th><th>地点</th><th>预算</th></tr></thead>
      <tbody>
        ${rows.map((item) => `
          <tr>
            <td>${html(item.meal_type || "-")}</td>
            <td class="plan-food"><strong>${html(item.name || "-")}</strong></td>
            <td>${html(item.location || "-")}</td>
            <td><span class="plan-price">${html(item.price_text || "-")}</span></td>
          </tr>
        `).join("")}
        <tr>
          <td>住宿</td>
          <td class="plan-food"><strong>${html(hotel.name || "-")}</strong></td>
          <td>${html(hotel.location || "-")}</td>
          <td><span class="plan-price">${html(hotel.price_text || "-")}</span></td>
        </tr>
      </tbody>
    </table>
  `;
}

function transportTable(day) {
  const rows = day.transport || [];
  if (!rows.length) return `<div class="plan-empty">当天暂无交通拆分，建议按地铁优先、短途步行的方式灵活出行</div>`;
  return `
    <table class="plan-table">
      <thead><tr><th>区间</th><th>方式</th><th>耗时</th><th>费用</th></tr></thead>
      <tbody>
        ${rows.map((item) => `
          <tr>
            <td>${html(`${item.from || "-"} →${item.to || "-"}`)}</td>
            <td>${html(item.mode || "-")}</td>
            <td><span class="plan-time">${html(item.duration || "-")}</span></td>
            <td><span class="plan-price">${html(item.price_text || "-")}</span></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function budgetChips(plan) {
  const rows = plan.budget_breakdown || [];
  if (!rows.length) return "";
  return `<div class="budget-chip-row">${rows.map((item) => `<span class="budget-chip">${html(item.name || "")}<b class="plan-price">${html(item.price_text || "-")}</b></span>`).join("")}</div>`;
}

function parsePriceAmount(text) {
  const raw = String(text || "").replace(/[^\d\-./]/g, "");
  if (!raw) return 0;
  const rangePart = raw.split("/")[0];
  const values = rangePart.split("-").map((x) => Number(x)).filter((x) => !Number.isNaN(x));
  if (!values.length) return 0;
  return values[values.length - 1];
}

function dayCostBreakdown(day) {
  const ticket = (day.schedule || []).reduce((sum, item) => sum + parsePriceAmount(item.price_text), 0);
  const meals = (day.meals || []).reduce((sum, item) => sum + parsePriceAmount(item.price_text), 0);
  const transport = (day.transport || []).reduce((sum, item) => sum + parsePriceAmount(item.price_text), 0);
  const hotel = parsePriceAmount((day.hotel || {}).price_text);
  const total = ticket + meals + transport + hotel;
  return { ticket, meals, transport, hotel, total };
}

function formatMoney(value) {
  return `¥${fmt(Number(value || 0))}`;
}

function routeTextOfDay(day) {
  const names = (day.schedule || []).map((item) => item.poi_name).filter(Boolean);
  return names.length ? names.join(" →") : "机动休整 / 自由活动";
}

function planOverviewCards(plan, days) {
  const totalPoi = days.reduce((sum, day) => sum + ((day.schedule || []).length || 0), 0);
  const totalMeals = days.reduce((sum, day) => sum + ((day.meals || []).length || 0), 0);
  const totalCost = Number(plan.budget_total || 0) || days.reduce((sum, day) => sum + dayCostBreakdown(day).total, 0);
  const budgetInput = Number(plan.budget_input || 0);
  return `
    <div class="plan-overview-grid">
      <section class="plan-overview-item">
        <span>行程天数</span>
        <strong>${days.length}</strong>
      </section>
      <section class="plan-overview-item">
        <span>路线点位</span>
        <strong>${totalPoi}</strong>
      </section>
      <section class="plan-overview-item">
        <span>餐食安排</span>
        <strong>${totalMeals}</strong>
      </section>
      <section class="plan-overview-item">
        <span>预计总费用</span>
        <strong>${formatMoney(totalCost)}</strong>
      </section>
      <section class="plan-overview-item">
        <span>你的预算</span>
        <strong>${budgetInput > 0 ? formatMoney(budgetInput) : "未填写"}</strong>
      </section>
      <section class="plan-overview-item">
        <span>预算匹配</span>
        <strong>${budgetInput > 0 ? `${Math.round((totalCost / Math.max(budgetInput, 1)) * 100)}%` : "自动"}</strong>
      </section>
    </div>
  `;
}

function renderAiPlan(data) {
  const pois = routePoisOf(data);
  const plan = data.local_plan || {};
  const days = plan.days || [];
  if (!days.length) {
    $("aiPlanSummary").innerHTML = `
      <h3>旅行规划概要</h3>
      <div class="plan-empty">当前没有足够的数据生成概要信息，请切换城市、主题或天数后再试一次</div>
    `;
    $("aiPlanResult").innerHTML = `
      <h3>详细行程暂未生成</h3>
      <div class="plan-empty">当前没有足够的数据生成路线。你可以切换城市、主题或天数后再试一次</div>
    `;
    renderLlmTable(data);
    $("aiPoiList").innerHTML = `<div class="plan-empty">暂无可展示的路线景点</div>`;
    renderAiMap([]);
    return;
  }
  $("aiPlanSummary").innerHTML = `
    <div class="plan-header">
      <h3>旅行规划概要</h3>
      <div class="plan-subtitle">${html(plan.title || "旅行方案")}</div>
      <p class="plan-overview-text">按地图上的顺序游玩即可，下面已经拆分好每天的路线、食宿和交通安排</p>
      ${planOverviewCards(plan, days)}
      ${budgetChips(plan)}
      <div class="plan-overview-list">
        ${days.map((day) => `
          <section class="plan-overview-day">
            <strong>Day ${day.day}</strong>
            <span>${html(day.theme || "当日安排")}</span>
            <div class="plan-route-line">${html(routeTextOfDay(day))}</div>
            <p>${html(day.route_note || "已按顺路方式安排当天行程")}</p>
            <div class="plan-day-cost-head">
              <b>当日费用</b>
              <strong>${formatMoney(dayCostBreakdown(day).total)}</strong>
            </div>
            <div class="plan-cost-split">
              ${(() => {
                const cost = dayCostBreakdown(day);
                const items = [
                  ["门票", cost.ticket],
                  ["餐饮", cost.meals],
                  ["交通", cost.transport],
                  ["住宿", cost.hotel],
                ];
                return items.map(([name, value]) => {
                  const percent = cost.total ? Math.round((value / cost.total) * 100) : 0;
                  return `<span>${html(name)} ${formatMoney(value)} · ${percent}%</span>`;
                }).join("");
              })()}
            </div>
          </section>
        `).join("")}
      </div>
    </div>
  `;
  $("aiPlanResult").innerHTML = `
    <div class="card-head detail-head"><h3>详细旅行规划</h3><span>按天查看路线、食宿、交通与提醒</span></div>
    <section class="plan-block">
      <div class="card-head"><h3>路线安排</h3><span>按 Day 顺序游玩即可，地图与下方点位一一对应</span></div>
      <div class="plan-day-grid">
        ${days.map((day) => `
          <article class="plan-day-card">
            <div class="plan-day-head">
              <strong>Day ${day.day}</strong>
              <span>${html(day.theme || "")}</span>
            </div>
            <p class="hint-text">${html(day.route_note || "")}</p>
            ${scheduleTable(day)}
          </article>
        `).join("")}
      </div>
    </section>
    <section class="plan-block">
      <div class="card-head"><h3>食宿安排</h3><span>每一天拆分到三餐与酒店，不再混成一段文本</span></div>
      <div class="plan-day-grid">
        ${days.map((day) => `
          <article class="plan-day-card">
            <div class="plan-day-head">
              <strong>Day ${day.day}</strong>
              <span>餐饮与住宿</span>
            </div>
            ${mealTable(day)}
          </article>
        `).join("")}
      </div>
    </section>
    <section class="plan-block">
      <div class="card-head"><h3>交通安全</h3><span>按每天列出区间、方式、耗时与费用</span></div>
      <div class="plan-day-grid">
        ${days.map((day) => `
          <article class="plan-day-card">
            <div class="plan-day-head">
              <strong>Day ${day.day}</strong>
              <span>交通拆分</span>
            </div>
            ${transportTable(day)}
          </article>
        `).join("")}
      </div>
    </section>
    <section class="plan-block">
      <div class="card-head"><h3>出行提醒</h3><span>标准化提示，天气、预约、交通和安全一次看全</span></div>
      <ul class="tip-list plan-tip-list">${(plan.tips || []).map((tip) => `<li>${html(tip)}</li>`).join("")}</ul>
    </section>
  `;
  renderLlmTable(data);
  $("aiPoiList").innerHTML = pois.length ? scenicCards(pois, pois.length) : `<div class="plan-empty">暂无路线景点可展示</div>`;
  bindCardActions($("aiPoiList"));
  renderAiMap(pois);
}

function renderAiMap(pois) {
  if (state.config.amap_key && window.AMap) {
    renderAmap(pois);
    return;
  }
  const chart = state.charts.aiMapBox;
  if (!chart) return;
  $("mapStatus").textContent = state.config.amap_key ? "高德脚本加载中，当前先使用坐标图展示路线顺序" : "未配置高德地图 Key，当前使用内置坐标图展示路线";
  const rows = pois.filter((x) => x.longitude && x.latitude);
  chart.setOption({
    ...baseChart(),
    tooltip: { formatter: (p) => `Day ${html(p.data.day)} · ${html(p.data.order)}<br>${html(p.data.name)}<br>${html(p.data.city)}<br>${html(p.data.period || "")} ${html(p.data.time || "")}` },
    grid: { left: 52, right: 22, top: 16, bottom: 44 },
    xAxis: { type: "value", name: "经度", min: 113, max: 123 },
    yAxis: { type: "value", name: "纬度", min: 23, max: 38 },
    dataZoom: [{ type: "inside", xAxisIndex: 0 }, { type: "inside", yAxisIndex: 0 }, { type: "slider", xAxisIndex: 0, bottom: 8 }, { type: "slider", yAxisIndex: 0, right: 4 }],
    series: [{
      type: "scatter",
      data: rows.map((row) => ({ name: row.poi_name, city: row.city_name, value: [row.longitude, row.latitude, row.heat_score || 1], day: row.day || 1, order: row.visit_order || 1, period: row.period || "", time: row.time_text || "" })),
      symbolSize: (v) => Math.max(16, Math.min(38, Number(v[2]) * 5)),
      itemStyle: { color: palette.teal, opacity: 0.9 },
      label: { show: true, formatter: (p) => `D${p.data.day}-${p.data.order} ${p.data.name}`, position: "right", fontSize: 11 },
    }],
  });
}

function renderAmap(pois) {
  const el = $("aiMapBox");
  if (state.charts.aiMapBox) {
    state.charts.aiMapBox.dispose();
    state.charts.aiMapBox = null;
  }
  el.innerHTML = "";
  const points = pois
    .filter((x) => x.longitude && x.latitude)
    .sort((a, b) => (Number(a.day || 0) - Number(b.day || 0)) || (Number(a.visit_order || 0) - Number(b.visit_order || 0)));
  const first = points[0];
  state.amap = new AMap.Map("aiMapBox", {
    zoom: 8,
    center: first ? [first.longitude, first.latitude] : [120.16, 30.25],
    dragEnable: true,
    scrollWheel: true,
    zoomEnable: true,
  });
  try {
    state.amap.addControl(new AMap.Scale());
    state.amap.addControl(new AMap.ToolBar());
  } catch {}
  if (!points.length) {
    $("mapStatus").textContent = "当前行程暂无可标注点位，切换城市、主题或天数后再试一次";
    return;
  }
  points.forEach((poi, index) => {
    const marker = new AMap.Marker({
      position: [poi.longitude, poi.latitude],
      title: poi.poi_name,
      content: `<div class="amap-order-marker"><small>D${poi.day || 1}</small><span>${poi.visit_order || index + 1}</span></div>`,
      offset: new AMap.Pixel(-15, -15),
    });
    const info = new AMap.InfoWindow({
      content: `<div style="padding:6px 4px;line-height:1.7"><strong>Day ${poi.day || 1} - ${poi.visit_order || index + 1} ${html(poi.poi_name)}</strong><br>${html(poi.city_name || "")}<br>${html(poi.period || "")} ${html(poi.time_text || "")}<br>热度：{dec(poi.heat_score, 1)}　评分：{dec(poi.comment_score, 1)}</div>`,
      offset: new AMap.Pixel(0, -28),
    });
    marker.on("click", () => info.open(state.amap, marker.getPosition()));
    marker.setMap(state.amap);
  });
  const overlays = [];
  const dayMap = new Map();
  points.forEach((poi) => {
    const day = Number(poi.day || 1);
    if (!dayMap.has(day)) dayMap.set(day, []);
    dayMap.get(day).push([poi.longitude, poi.latitude]);
  });
  dayMap.forEach((path, day) => {
    if (path.length < 2) return;
    const polyline = new AMap.Polyline({
      path,
      strokeColor: day % 2 ? "#418d68" : "#79b55b",
      strokeWeight: 5,
      strokeOpacity: 0.86,
      lineJoin: "round",
    });
    state.amap.add(polyline);
    overlays.push(polyline);
  });
  if (overlays.length) state.amap.setFitView(overlays);
  else if (points.length) state.amap.setFitView();
  $("mapStatus").textContent = `已接入高德地图，当前共标注${points.length} 个路线点位；标注顺序与下方 Day 行程一致。`;
}

function startClockAndLocation() {
  const update = () => {
    const text = new Date().toLocaleString("zh-CN", { hour12: false });
    setText("topClock", text);
    setText("homeClock", text);
    setText("screenClock", text);
    setText("commentNow", `当前时间：{text}`);
  };
  update();
  clearInterval(window.__travelClockTimer);
  window.__travelClockTimer = setInterval(update, 1000);
  if (!navigator.geolocation) {
    setText("homeLocation", "默认上海");
    setText("screenLocation", "默认上海");
    loadWeather(31.2304, 121.4737);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      setText("homeLocation", `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`);
      setText("screenLocation", `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`);
      loadWeather(latitude, longitude);
    },
    () => {
      setText("homeLocation", "默认上海");
      setText("screenLocation", "默认上海");
      loadWeather(31.2304, 121.4737);
    },
    { timeout: 8000 },
  );
}

async function loadWeather(lat, lon) {
  try {
    const data = await fetchJson(`/api/weather/current?lat=${lat}&lon=${lon}`);
    const locationText = data.location || `${Number(lat).toFixed(3)}, ${Number(lon).toFixed(3)}`;
    setText("homeLocation", locationText);
    setText("screenLocation", locationText);
    if (data.temperature === null || data.temperature === undefined) {
      setText("homeWeather", "天气暂不可用");
      setText("screenWeather", "天气暂不可用");
      return;
    }
    const weatherText = data.weather ? `${data.weather} · ` : "";
    const windText = windSummary(data);
    const weatherLine = `${weatherText}${dec(data.temperature, 1)}℃${windText ? ` · ${windText}` : ""}`;
    setText("homeWeather", weatherLine);
    setText("screenWeather", weatherLine);
  } catch {
    setText("homeWeather", "天气暂不可用");
    setText("screenWeather", "天气暂不可用");
  }
}

function loadAmapScript() {
  if (!state.config.amap_key || window.AMap) return Promise.resolve(!!window.AMap);
  if (state.amapScriptPromise) return state.amapScriptPromise;
  state.amapScriptPromise = new Promise((resolve) => {
    const existed = Array.from(document.scripts).find((script) => (script.src || "").includes("webapi.amap.com/maps"));
    const finalize = () => {
      let count = 0;
      const timer = setInterval(() => {
        count += 1;
        if (window.AMap) {
          clearInterval(timer);
          state.amapReady = true;
          resolve(true);
        } else if (count >= 20) {
          clearInterval(timer);
          state.amapReady = false;
          resolve(false);
        }
      }, 150);
    };
    if (existed) {
      finalize();
      return;
    }
    const script = document.createElement("script");
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(state.config.amap_key)}&plugin=AMap.Scale,AMap.ToolBar`;
    script.async = true;
    script.defer = true;
    script.onload = finalize;
    script.onerror = () => {
      state.amapReady = false;
      resolve(false);
    };
    document.head.appendChild(script);
  });
  return state.amapScriptPromise;
}

function loadLeafletAssets() {
  if (window.L) return Promise.resolve(true);
  if (state.leafletPromise) return state.leafletPromise;
  state.leafletPromise = new Promise((resolve) => {
    if (!document.getElementById("leaflet-style")) {
      const link = document.createElement("link");
      link.id = "leaflet-style";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }
    const existed = Array.from(document.scripts).find((script) => (script.src || "").includes("leaflet@1.9.4"));
    const done = () => resolve(!!window.L);
    if (existed) {
      setTimeout(done, 200);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.async = true;
    script.onload = done;
    script.onerror = () => resolve(false);
    document.head.appendChild(script);
  });
  return state.leafletPromise;
}

async function renderAiMap(pois) {
  const rows = (pois || []).filter((x) => x.longitude && x.latitude);
  if (state.config.amap_key) {
    const ready = window.AMap ? true : await loadAmapScript().catch(() => false);
    if (ready && window.AMap) {
      renderAmap(rows);
      return;
    }
    const leafletReady = await loadLeafletAssets().catch(() => false);
    if (leafletReady && window.L) {
      renderLeafletMap(rows);
      return;
    }
  }
  const chart = state.charts.aiMapBox;
  if (!chart) return;
  setText("mapStatus", "地图服务暂不可用，当前显示路线坐标图");
  chart.resize();
  chart.setOption({
    ...baseChart(),
    tooltip: { formatter: (p) => `Day ${html(p.data.day)} · 第${html(p.data.order)} 位<br>${html(p.data.name)}<br>${html(p.data.city)}` },
    grid: { left: 52, right: 22, top: 16, bottom: 44 },
    xAxis: { type: "value", name: "经度", min: 113, max: 123 },
    yAxis: { type: "value", name: "纬度", min: 23, max: 38 },
    dataZoom: [{ type: "inside", xAxisIndex: 0 }, { type: "inside", yAxisIndex: 0 }, { type: "slider", xAxisIndex: 0, bottom: 8 }, { type: "slider", yAxisIndex: 0, right: 4 }],
    series: [{
      type: "scatter",
      data: rows.map((row) => ({ name: row.poi_name, city: row.city_name, value: [row.longitude, row.latitude, row.heat_score || 1], day: row.day || 1, order: row.visit_order || 1 })),
      symbolSize: (v) => Math.max(16, Math.min(38, Number(v[2]) * 5)),
      itemStyle: { color: palette.teal, opacity: 0.9 },
      label: { show: true, formatter: (p) => `D${p.data.day}-${p.data.order}`, position: "right", fontSize: 11 },
    }],
  });
}

function renderAmap(pois) {
  const el = $("aiMapBox");
  if (!el) return;
  if (el.clientWidth < 40 || el.clientHeight < 40) {
    setTimeout(() => renderAmap(pois), 180);
    return;
  }
  if (!window.AMap) {
    renderAiMap(pois);
    return;
  }
  if (state.leafletMap) {
    state.leafletMap.remove();
    state.leafletMap = null;
  }
  if (state.charts.aiMapBox) {
    state.charts.aiMapBox.dispose();
    state.charts.aiMapBox = null;
  }
  el.innerHTML = "";
  const points = (pois || [])
    .filter((x) => x.longitude && x.latitude)
    .sort((a, b) => (Number(a.day || 0) - Number(b.day || 0)) || (Number(a.visit_order || 0) - Number(b.visit_order || 0)));
  const first = points[0];
  state.amap = new AMap.Map("aiMapBox", {
    zoom: 8,
    center: first ? [first.longitude, first.latitude] : [121.4737, 31.2304],
    dragEnable: true,
    scrollWheel: true,
    zoomEnable: true,
  });
  try {
    state.amap.addControl(new AMap.Scale());
    state.amap.addControl(new AMap.ToolBar());
  } catch {}
  if (!points.length) {
    setText("mapStatus", "当前行程暂无可标注点位，切换城市、主题或天数后再试一次");
    return;
  }
  points.forEach((poi, index) => {
    const marker = new AMap.Marker({
      position: [poi.longitude, poi.latitude],
      title: poi.poi_name,
      content: `<div class="amap-order-marker"><small>D${poi.day || 1}</small><span>${poi.visit_order || index + 1}</span></div>`,
      offset: new AMap.Pixel(-15, -15),
    });
    const info = new AMap.InfoWindow({
      content: `<div style="padding:6px 4px;line-height:1.7"><strong>Day ${poi.day || 1} - ${poi.visit_order || index + 1} ${html(poi.poi_name)}</strong><br>${html(poi.city_name || "")}<br>${html(poi.period || "")} ${html(poi.time_text || "")}<br>热度：{dec(poi.heat_score, 1)}　评分：{dec(poi.comment_score, 1)}</div>`,
      offset: new AMap.Pixel(0, -28),
    });
    marker.on("click", () => info.open(state.amap, marker.getPosition()));
    marker.setMap(state.amap);
  });
  const overlays = [];
  const dayMap = new Map();
  points.forEach((poi) => {
    const day = Number(poi.day || 1);
    if (!dayMap.has(day)) dayMap.set(day, []);
    dayMap.get(day).push([poi.longitude, poi.latitude]);
  });
  dayMap.forEach((path, day) => {
    if (path.length < 2) return;
    const polyline = new AMap.Polyline({
      path,
      strokeColor: day % 2 ? "#418d68" : "#79b55b",
      strokeWeight: 5,
      strokeOpacity: 0.86,
      lineJoin: "round",
    });
    state.amap.add(polyline);
    overlays.push(polyline);
  });
  if (overlays.length) state.amap.setFitView(overlays);
  else state.amap.setFitView();
  setText("mapStatus", `已接入高德地图，当前共标注${points.length} 个路线点位；标注顺序与下方 Day 行程一致。`);
}

function renderLeafletMap(pois) {
  const el = $("aiMapBox");
  if (!el) return;
  if (el.clientWidth < 40 || el.clientHeight < 40) {
    setTimeout(() => renderLeafletMap(pois), 180);
    return;
  }
  if (state.charts.aiMapBox) {
    state.charts.aiMapBox.dispose();
    state.charts.aiMapBox = null;
  }
  if (state.amap && typeof state.amap.destroy === "function") {
    try { state.amap.destroy(); } catch {}
    state.amap = null;
  }
  el.innerHTML = "";
  const points = (pois || [])
    .filter((x) => x.longitude && x.latitude)
    .sort((a, b) => (Number(a.day || 0) - Number(b.day || 0)) || (Number(a.visit_order || 0) - Number(b.visit_order || 0)));
  if (!points.length) {
    setText("mapStatus", "当前行程暂无可标注点位，切换城市、主题或天数后再试一次");
    return;
  }
  state.leafletMap = L.map(el, { zoomControl: true, scrollWheelZoom: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap",
  }).addTo(state.leafletMap);
  const latlngs = points.map((poi) => [Number(poi.latitude), Number(poi.longitude)]);
  points.forEach((poi, index) => {
    const marker = L.marker([Number(poi.latitude), Number(poi.longitude)]).addTo(state.leafletMap);
    marker.bindPopup(`<div style="line-height:1.7"><strong>Day ${poi.day || 1} - ${poi.visit_order || index + 1} ${html(poi.poi_name)}</strong><br>${html(poi.city_name || "")}<br>热度：{dec(poi.heat_score, 1)}　评分：{dec(poi.comment_score, 1)}</div>`);
    marker.bindTooltip(`D${poi.day || 1}-${poi.visit_order || index + 1}`, { permanent: true, direction: "top", offset: [0, -12] });
  });
  if (latlngs.length >= 2) L.polyline(latlngs, { color: "#4f9f80", weight: 5, opacity: 0.85 }).addTo(state.leafletMap);
  state.leafletMap.fitBounds(latlngs, { padding: [26, 26] });
  setText("mapStatus", `高德地图暂未完成加载，已自动切换为交互地图；当前共标注${points.length} 个路线点位。`);
}

async function bootstrap() {
  const hasSession = restoreSession();
  initCharts();
  bindUI();
  updateViewSwitches();
  startClockAndLocation();
  if (hasSession) {
    updateProfileUI();
    showAppAfterAuth(true);
  }
  [state.config, state.frontend, state.flow] = await Promise.all([
    fetchJson("/api/config").catch(() => ({})),
    fetchJson("/api/frontend-modules").catch((error) => {
      console.error("frontend modules load failed", error);
      return emptyFrontendBundle();
    }),
    fetchJson("/api/flow-module").catch((error) => {
      console.error("flow module load failed", error);
      return emptyFlowBundle();
    }),
  ]);
  renderHero();
  renderHome();
  await loadHomeNews();
  clearInterval(window.__homeNewsTimer);
  window.__homeNewsTimer = setInterval(() => loadHomeNews().catch(() => {}), 15 * 60 * 1000);
  buildRegionSelectors();
  renderRegion();
  buildFilterSelectors();
  renderFilter();
  buildRankTabs();
  renderRanking();
  buildRecommendSelector();
  renderRecommend();
  buildForecastSelector();
  renderFlow();
  renderImpact();
  renderCluster();
  await renderPortrait();
  renderBigScreen();
  await buildAiAssistant();
  updateProfileUI();
  renderPlans();
  if (hasSession) {
    updateProfileUI();
    showAppAfterAuth();
    await loadFavorites();
    await loadMyComments();
    await loadPlans();
    showAppAfterAuth();
    if (state.role === "operator") await renderPortrait(true);
  }
}

bootstrap().catch((error) => {
  console.error(error);
  document.body.innerHTML = `<div class="fatal-error"><h1>页面加载失败</h1><p>${html(error.message)}</p><p>请确认本地服务和 MySQL 已启动</p></div>`;
});
