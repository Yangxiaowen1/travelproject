const metricConfig = [
  ["poi_total", "景点总数"],
  ["city_total", "覆盖城市"],
  ["region_total", "覆盖区域"],
  ["avg_price", "平均价格"],
  ["avg_score", "平均评分"],
  ["avg_heat", "平均热度"],
  ["total_comments", "累计评论"],
  ["free_poi_total", "免费景点"],
  ["promotion_poi_total", "优惠景点"],
  ["video_poi_total", "含视频景点"],
];

let activeRecommendName = "";

function formatNumber(value) {
  if (typeof value !== "number") return value ?? "-";
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatDecimal(value) {
  if (typeof value !== "number") return value ?? "-";
  return value.toFixed(2);
}

function createMetricCards(overview) {
  const grid = document.getElementById("metricGrid");
  grid.innerHTML = metricConfig
    .map(([key, label]) => {
      const value = key.includes("avg_") ? formatDecimal(overview[key]) : formatNumber(overview[key]);
      return `
        <div class="metric-card">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `;
    })
    .join("");
}

function createCityTable(rows) {
  const body = document.getElementById("cityTableBody");
  body.innerHTML = rows
    .slice(0, 20)
    .map(
      (row) => `
        <tr>
          <td>${row.city_name}</td>
          <td>${formatNumber(row.poi_count)}</td>
          <td>${formatDecimal(row.avg_price)}</td>
          <td>${formatDecimal(row.avg_score)}</td>
          <td>${formatDecimal(row.avg_heat)}</td>
          <td>${formatNumber(row.total_comments)}</td>
        </tr>
      `,
    )
    .join("");
}

function createBars(containerId, rows, labelKey, valueKey, limit = 10) {
  const container = document.getElementById(containerId);
  const topRows = rows.slice(0, limit);
  const maxValue = Math.max(...topRows.map((item) => Number(item[valueKey]) || 0), 1);
  container.innerHTML = topRows
    .map((row) => {
      const value = Number(row[valueKey]) || 0;
      const percent = Math.max(8, (value / maxValue) * 100);
      return `
        <div class="bar-row">
          <div class="bar-label">${row[labelKey]}</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${percent}%"></div>
          </div>
          <div class="bar-value">${formatNumber(value)}</div>
        </div>
      `;
    })
    .join("");
}

function createRegionList(rows) {
  const container = document.getElementById("regionList");
  container.innerHTML = rows
    .slice(0, 8)
    .map(
      (row) => `
        <div class="region-item">
          <div class="region-title">
            <span>${row.city_name} / ${row.region_name}</span>
            <span>热度 ${formatDecimal(row.avg_heat)}</span>
          </div>
          <div class="region-meta">
            景点数 ${formatNumber(row.poi_count)} ，评分 ${formatDecimal(row.avg_score)} ，评论量 ${formatNumber(row.total_comments)}
          </div>
        </div>
      `,
    )
    .join("");
}

function createPoiList(containerId, rows, mode) {
  const container = document.getElementById(containerId);
  container.innerHTML = rows
    .slice(0, 10)
    .map((row) => {
      const sideValue =
        mode === "heat"
          ? `热度 ${formatDecimal(row.heat_score)}`
          : `评论 ${formatNumber(row.comment_count)}`;
      return `
        <div class="poi-item">
          <div class="poi-title">
            <a href="${row.detail_url || "#"}" target="_blank" rel="noreferrer">${row.poi_name}</a>
            <span>${sideValue}</span>
          </div>
          <div class="poi-meta">
            ${row.city_name} / ${row.region_name || "未知区域"} ｜ 价格 ${formatDecimal(row.price || 0)} ｜ 评分 ${formatDecimal(row.comment_score || 0)} ｜ 标签 ${row.tag_names || "暂无"}
          </div>
        </div>
      `;
    })
    .join("");
}

function createRecommendButtons(names) {
  const container = document.getElementById("recommendToolbar");
  container.innerHTML = names
    .map(
      (name) => `
        <button class="recommend-chip ${name === activeRecommendName ? "active" : ""}" data-name="${name}">
          ${name}
        </button>
      `,
    )
    .join("");

  Array.from(container.querySelectorAll(".recommend-chip")).forEach((button) => {
    button.addEventListener("click", () => {
      const name = button.getAttribute("data-name") || "";
      loadRecommendations(name);
    });
  });
}

function createRecommendationList(name, rows) {
  const meta = document.getElementById("recommendMeta");
  const container = document.getElementById("recommendList");
  meta.textContent = `${name} 的推荐结果，共展示 ${rows.length} 条。每条结果都带有推荐原因。`;
  container.innerHTML = rows
    .map(
      (row) => `
        <div class="poi-item">
          <div class="poi-title">
            <a href="${row.detail_url || "#"}" target="_blank" rel="noreferrer">${row.target_poi_name}</a>
            <span>推荐分 ${formatDecimal(row.recommend_score)}</span>
          </div>
          <div class="poi-meta">
            ${row.target_city_name} / ${row.target_region_name || "未知区域"} ｜ 价格 ${formatDecimal(row.target_price || 0)} ｜ 评分 ${formatDecimal(row.target_comment_score || 0)} ｜ 热度 ${formatDecimal(row.target_heat_score || 0)}
          </div>
          <div class="poi-meta">
            推荐原因：${row.reason_text || "综合特征相近"}
          </div>
        </div>
      `,
    )
    .join("");
}

function updateStatus(text, hint) {
  document.getElementById("dataStatus").textContent = text;
  document.getElementById("dataHint").textContent = hint;
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`请求失败: ${path}`);
  }
  const result = await response.json();
  if (!result.success) {
    throw new Error(result.message || `接口返回失败: ${path}`);
  }
  return result.data;
}

async function loadRecommendations(name) {
  if (!name) return;
  activeRecommendName = name;
  createRecommendButtons(document.recommendSampleNames || []);
  const recommendData = await fetchJson(`/api/recommendations?poi_name=${encodeURIComponent(name)}&limit=6`);
  createRecommendationList(recommendData.matched_name || name, recommendData.recommendations || []);
  createRecommendButtons(document.recommendSampleNames || []);
}

async function bootstrap() {
  try {
    updateStatus("加载中", "正在读取分析结果");
    const [overview, cityStats, priceBuckets, scoreBuckets, hotPoi, commentPoi, tagSummary, regionHeat, recommendSamples] =
      await Promise.all([
        fetchJson("/api/overview"),
        fetchJson("/api/city-stats"),
        fetchJson("/api/price-buckets"),
        fetchJson("/api/score-buckets"),
        fetchJson("/api/hot-poi-top100"),
        fetchJson("/api/comment-top100"),
        fetchJson("/api/tag-summary"),
        fetchJson("/api/region-heat-top300"),
        fetchJson("/api/recommendation-samples"),
      ]);

    createMetricCards(overview);
    createCityTable(cityStats);
    createBars("priceBars", priceBuckets, "price_bucket", "poi_count", 8);
    createBars("scoreBars", scoreBuckets, "score_bucket", "poi_count", 8);
    createBars("tagBars", tagSummary, "tag_name", "poi_count", 12);
    createRegionList(regionHeat);
    createPoiList("hotPoiList", hotPoi, "heat");
    createPoiList("commentPoiList", commentPoi, "comment");

    document.recommendSampleNames = Object.keys(recommendSamples.samples || {});
    activeRecommendName = document.recommendSampleNames[0] || "";
    createRecommendButtons(document.recommendSampleNames);
    if (activeRecommendName) {
      await loadRecommendations(activeRecommendName);
    }

    updateStatus("加载完成", `已展示 ${formatNumber(overview.poi_total)} 条清洗后景点数据`);
  } catch (error) {
    updateStatus("加载失败", "请确认本地服务已经启动");
    console.error(error);
  }
}

bootstrap();
