/* ===== ANIMA TAGS frontend (Unified Dressing & Background Gallery) ================ */
'use strict';

// 1. App State
const state = {
  mode: 'clothing', // 'clothing' (服饰) 或 'background' (背景)
  q: '',
  sort: 'id-asc',
  filters: {
    categories: new Set(),
    folders: new Set(),
    traits: new Set()
  },
  source: 'cdn', // 默认使用 CDN 加载以防 GitHub Pages 的本地路径缓存死锁
  displayLang: 'bilingual', // 'bilingual' (中英双语) 或 'en' (纯英文)
};

let clothingData = [];
let backgroundData = [];
let filteredData = [];
let allTraits = []; // { name: string, count: number }

const CDN_URLS = {
  clothing: "https://cdn.jsdelivr.net/gh/nregret/Dressing-doll@main/clothing_data.json",
  background: "https://cdn.jsdelivr.net/gh/nregret/AnimaTags-DB@main/background_data.json"
};

const LOCAL_URLS = {
  clothing: "./clothing_data.json",
  background: "./background_data.json"
};

// 2. DOM Elements
const $ = s => document.querySelector(s);
const galleryEl   = $('#gallery');
const resultEl    = $('#resultcount');
const clearBtn    = $('#clearall');
const facetsEl    = $('#facets');
const chipsEl     = $('#chips');
const searchEl    = $('#q');
const langSelect  = $('#lang-select');
const modeSwitcher = $('#mode-switcher');
const brandToggle  = $('#brand-toggle');

// 3. Initialize
async function init() {
  setupEventListeners();
  setupModeToggle();
  await loadData();
}

// 4. Data Fetching & Caching
async function loadData() {
  const mode = state.mode;
  const cachedData = mode === 'clothing' ? clothingData : backgroundData;

  // 1. 内存缓存存在时，直接秒切
  if (cachedData && cachedData.length > 0) {
    console.log(`[AnimaTags] Using memory cached data for: ${mode}`);
    extractMetadata();
    renderFacets();
    applyFiltersAndSort();
    return;
  }

  // 2. 否则，开始加载数据
  let url = LOCAL_URLS[mode];
  if (state.source === 'cdn') {
    // 动态获取 GitHub 的最新提交 SHA，避开 jsDelivr 缓存死锁
    const repo = mode === 'clothing' ? "nregret/Dressing-doll" : "nregret/AnimaBackground";
    const defaultCdn = CDN_URLS[mode];
    try {
      const shaResp = await fetch(`https://api.github.com/repos/${repo}/commits/main`, { cache: "no-store" });
      if (shaResp.ok) {
        const shaJson = await shaResp.json();
        if (shaJson && shaJson.sha) {
          url = `https://cdn.jsdelivr.net/gh/${repo}@${shaJson.sha}/${mode === 'clothing' ? 'clothing' : 'background'}_data.json`;
          console.log(`[AnimaTags] Dynamic CDN URL matched for ${mode}:`, shaJson.sha);
        } else {
          url = defaultCdn;
        }
      } else {
        url = defaultCdn;
      }
    } catch (e) {
      console.warn(`[AnimaTags] Failed to fetch latest commit SHA for ${mode}, fallback to @main`, e);
      url = defaultCdn;
    }
  } else {
    // 本地加载时拼接时间戳，防止浏览器强缓存
    url = `${LOCAL_URLS[mode]}?_t=${Date.now()}`;
  }

  toast(`Loading ${mode === 'clothing' ? 'Clothing' : 'Background'} database...`);
  
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    let data = await response.json();
    
    // 针对背景数据进行 duplicate 过滤
    if (mode === 'background') {
      data = data.filter(item => !item.duplicate);
    }

    if (mode === 'clothing') {
      clothingData = data;
    } else {
      backgroundData = data;
    }
    
    extractMetadata();
    renderFacets();
    applyFiltersAndSort();
    toast(`${mode === 'clothing' ? 'Clothing' : 'Background'} loaded! 🌸`);
  } catch (error) {
    console.error(`Failed to load ${mode} database:`, error);
    toast("Load failed. Trying local backup...");
    if (state.source !== 'local') {
      state.source = 'local';
      await loadData();
    }
  }
}

// Count Traits occurrences and sort
function extractMetadata() {
  const data = state.mode === 'clothing' ? clothingData : backgroundData;
  const countMap = new Map();
  data.forEach(item => {
    if (item.traits && Array.isArray(item.traits)) {
      item.traits.forEach(t => {
        countMap.set(t, (countMap.get(t) || 0) + 1);
      });
    }
  });
  
  allTraits = Array.from(countMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
}

// 5. Helpers
function debounce(fn, ms){
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

// 合并后的全量服饰与物理背景细分特征中英文映射表
const TRAITS_TRANSLATION = {
  // --- 服饰特征 (Clothing) ---
  "apron": "围裙",
  "backless": "露背",
  "bare legs": "光腿",
  "boots": "靴子",
  "collar": "衣领",
  "garter belt": "吊袜带",
  "glasses": "眼镜",
  "gloves": "手套",
  "halterneck": "吊颈/挂脖",
  "high heels": "高跟鞋",
  "kneehighs": "及膝袜",
  "lace": "蕾丝",
  "latex": "乳胶",
  "leather": "皮革",
  "miniskirt": "超短裙",
  "off-shoulder": "露肩/一字领",
  "pantyhose": "连裤袜",
  "ribbon": "丝带/蝴蝶结",
  "short shorts": "超短裤",
  "side slit": "侧开叉",
  "silk": "丝绸",
  "sleeveless": "无袖",
  "thighhighs": "大腿袜",
  "tie": "领带/系带",
  "translucent": "半透明",
  
  // --- 物理背景特征 (Background) ---
  "indoor": "室内",
  "outdoor": "室外",
  "day": "白昼",
  "night": "夜景",
  "water": "水体/水面",
  "snowy": "雪景/寒冷",
  "greenery": "绿植/植被",
  "neon": "霓虹/科技",
  "sunlight": "阳光",
  "street": "街道/都市",
  "classroom": "校园/教室",
  "home": "日常/居家",
  "japanese": "日式/和风",
  "ruins": "废墟/末世",
  "cyber": "科幻/赛博",
  "sky": "天空/云朵",
  "stars": "星空/银河",
  "sea": "海洋/沙滩",
  "forest": "森林/林间",
  "flower": "花卉/植物",
  "sunset": "黄昏/夕阳",
  "rainy": "雨天/潮湿",
  "cozy": "温馨/舒适"
};

function getTraitZh(enTrait) {
  if (!enTrait) return '';
  const key = enTrait.toLowerCase().trim();
  if (TRAITS_TRANSLATION[key]) {
    return TRAITS_TRANSLATION[key];
  }
  
  // 动态后备：尝试从现有数据集的 tags 双语翻译中捕获
  const data = state.mode === 'clothing' ? clothingData : backgroundData;
  for (const item of data) {
    if (!item.tags || !item.tags_zh) continue;
    const enList = item.tags.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
    const zhList = item.tags_zh.split(',').map(t => t.trim()).filter(Boolean);
    const idx = enList.indexOf(key);
    if (idx !== -1 && zhList[idx]) {
      return zhList[idx];
    }
  }
  return enTrait;
}

function fmt(n){
  if (n >= 1e6) return (n/1e6).toFixed(1).replace(/\.0$/,'') + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(1).replace(/\.0$/,'') + 'K';
  return '' + n;
}

let toastTimer;
function toast(msg){
  const el = $('#toast');
  el.innerHTML = `<b>✦</b> ${esc(msg)}`;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 1700);
}

async function copyText(text, note){
  const cleanText = text.replace(/,\s*$/, "").trim();
  try {
    await navigator.clipboard.writeText(cleanText);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = cleanText; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); ta.remove();
  }
  toast(note);
}

// 6. UI Render: Facets sidebar
function renderFacets() {
  const categoriesList = state.mode === 'clothing'
    ? [
        "礼服/裙装 (Dress & Gown)",
        "日常/休闲 (Casual & Daily)",
        "制服/西服 (Uniform & Suit)",
        "泳装/内衣 (Swimsuit & Lingerie)",
        "角色扮演/奇幻 (Fantasy & Cosplay)",
        "性感/暴露 (Revealing)"
      ]
    : [
        "自然与户外 (Nature & Outdoors)",
        "都市与日常 (Urban & Daily)",
        "幻想与异界 (Fantasy & Sci-Fi)",
        "极简与纯色 (Minimalist & Abstract)"
      ];
  
  let html = '';

  // 1. Categories Facet
  html += `
    <div class="fgroup">
      <div class="fgroup-head">
        <span class="ti">Categories (${state.mode === 'clothing' ? '大品类' : '场景大类'})</span>
      </div>
      <div class="fgroup-body">
        <div class="flist">
  `;
  categoriesList.forEach(cat => {
    const isChecked = state.filters.categories.has(cat) ? 'checked' : '';
    const isOn = isChecked ? 'on' : '';
    const displayCat = state.displayLang === 'en' ? (cat.match(/\(([^)]+)\)/)?.[1] || cat) : cat;
    html += `
      <label class="fopt ${isOn}">
        <input type="checkbox" class="cat-filter" value="${esc(cat)}" ${isChecked}>
        <span class="box"></span>
        <span class="fl">${esc(displayCat)}</span>
      </label>
    `;
  });
  html += `</div></div></div>`;

  // 3. Traits Facet
  html += `
    <div class="fgroup searchable">
      <div class="fgroup-head">
        <span class="ti">Traits (${state.mode === 'clothing' ? '细分特征' : '背景特征'})</span>
      </div>
      <div class="fgroup-body">
        <div class="flist">
  `;
  allTraits.forEach(t => {
    const isChecked = state.filters.traits.has(t.name) ? 'checked' : '';
    const isOn = isChecked ? 'on' : '';
    const traitZh = getTraitZh(t.name);
    const displayTrait = (traitZh && state.displayLang === 'bilingual')
      ? `${esc(t.name)} <span style="font-size:0.75rem; color:rgba(255,255,255,0.4); font-weight:normal;">(${esc(traitZh)})</span>`
      : esc(t.name);
    html += `
      <label class="fopt ${isOn}">
        <input type="checkbox" class="trait-filter" value="${esc(t.name)}" ${isChecked}>
        <span class="box"></span>
        <span class="fl">${displayTrait}</span>
      </label>
    `;
  });
  html += `</div></div></div>`;

  facetsEl.innerHTML = html;

  // Bind sidebar checkbox events
  facetsEl.querySelectorAll('.cat-filter').forEach(cb => {
    cb.addEventListener('change', e => {
      const label = cb.closest('.fopt');
      if (e.target.checked) {
        state.filters.categories.add(e.target.value);
        if (label) label.classList.add('on');
      } else {
        state.filters.categories.delete(e.target.value);
        if (label) label.classList.remove('on');
      }
      applyFiltersAndSort();
    });
  });

  facetsEl.querySelectorAll('.trait-filter').forEach(cb => {
    cb.addEventListener('change', e => {
      const label = cb.closest('.fopt');
      if (e.target.checked) {
        state.filters.traits.add(e.target.value);
        if (label) label.classList.add('on');
      } else {
        state.filters.traits.delete(e.target.value);
        if (label) label.classList.remove('on');
      }
      applyFiltersAndSort();
    });
  });
}

// 7. Core Filtering & Sorting
function applyFiltersAndSort() {
  const data = state.mode === 'clothing' ? clothingData : backgroundData;

  filteredData = data.filter(item => {
    // A. Global text search
    if (state.q) {
      const q = state.q.toLowerCase().trim();
      
      const aliases = state.mode === 'clothing' ? {
        "丝袜": ["长筒袜", "连裤袜", "大腿袜", "stockings", "thighhighs", "pantyhose", "lace thighhigh", "leggings"],
        "袜子": ["长筒袜", "连裤袜", "大腿袜", "stockings", "thighhighs", "pantyhose", "socks", "legwear"],
        "高跟鞋": ["high heels", "heels", "pumps", "stiletto"],
        "手套": ["gloves", "gloves", "mittens"],
        "裙": ["dress", "skirt", "gown", "连衣裙", "半身裙", "礼服", "裙装"],
        "内衣": ["lingerie", "panties", "underwear", "bra", "undergarment"]
      } : {
        "水": ["water", "sea", "river", "lake", "pool", "puddle", "水体", "水面", "海", "河", "湖"],
        "树": ["forest", "tree", "wood", "greenery", "bamboo", "birch", "植物", "绿植", "森林", "竹林"],
        "天空": ["sky", "stars", "galaxy", "milky way", "cloud", "sunlight", "sunset", "星空", "黄昏", "太阳"],
        "夜": ["night", "stars", "neon", "cyber", "夜景", "星空", "霓虹"],
        "雪": ["snow", "winter", "ice", "snowy", "雪景", "冬天", "冰"]
      };
      
      let qList = [q];
      for (const [key, val] of Object.entries(aliases)) {
        if (q.includes(key)) {
          qList = qList.concat(val);
        }
      }
      
      const matchesName = qList.some(kw => 
        item.name.toLowerCase().includes(kw) || 
        (item.name_zh && item.name_zh.toLowerCase().includes(kw))
      );
      const matchesTags = qList.some(kw => 
        item.tags.toLowerCase().includes(kw) || 
        (item.tags_zh && item.tags_zh.toLowerCase().includes(kw))
      );
      const matchesId = item.id.includes(q);
      
      if (!matchesName && !matchesTags && !matchesId) return false;
    }

    // B. Category filter (OR logic)
    if (state.filters.categories.size > 0) {
      const match = item.categories.some(cat => state.filters.categories.has(cat));
      if (!match) return false;
    }

    // C. Traits filter (AND logic)
    if (state.filters.traits.size > 0) {
      const matchAll = Array.from(state.filters.traits).every(t => item.traits.includes(t));
      if (!matchAll) return false;
    }

    return true;
  });

  // Sort
  if (state.sort === 'id-desc') {
    filteredData.sort((a, b) => b.id.localeCompare(a.id));
  } else if (state.sort === 'id-asc') {
    filteredData.sort((a, b) => a.id.localeCompare(b.id));
  } else if (state.sort === 'az') {
    filteredData.sort((a, b) => a.name.localeCompare(b.name));
  }

  renderChips();
  renderGallery();
}

// Render active filter chips
function renderChips() {
  let html = '';
  
  for (const cat of state.filters.categories) {
    const displayCat = state.displayLang === 'en' ? (cat.match(/\(([^)]+)\)/)?.[1] || cat) : cat.split(" ")[0];
    const catHeader = state.displayLang === 'en' ? 'Category' : (state.mode === 'clothing' ? '大品类' : '大类');
    html += `<span class="achip" data-type="cat" data-val="${esc(cat)}"><span class="cat">${catHeader}</span>${esc(displayCat)} <button class="x">×</button></span>`;
  }
  for (const trait of state.filters.traits) {
    const zh = getTraitZh(trait);
    const display = (zh && state.displayLang === 'bilingual') ? `${trait} (${zh})` : trait;
    const traitHeader = state.displayLang === 'en' ? 'Trait' : '特征';
    html += `<span class="achip" data-type="trait" data-val="${esc(trait)}"><span class="cat">${traitHeader}</span>${esc(display)} <button class="x">×</button></span>`;
  }

  chipsEl.innerHTML = html;
  
  const hasFilters = state.filters.categories.size > 0 || state.filters.traits.size > 0;
  clearBtn.hidden = !hasFilters;
  clearBtn.textContent = state.displayLang === 'en' ? 'Clear All' : '清除全部';

  // Bind chip remove events
  chipsEl.querySelectorAll('.achip').forEach(chip => {
    chip.querySelector('.x').addEventListener('click', () => {
      const type = chip.dataset.type;
      const val = chip.dataset.val;
      
      if (type === 'cat') state.filters.categories.delete(val);
      else if (type === 'trait') state.filters.traits.delete(val);
      
      renderFacets();
      applyFiltersAndSort();
    });
  });
}

// 8. Render Grid Cards
function renderGallery() {
  const isClothing = state.mode === 'clothing';
  
  const resultText = state.displayLang === 'en' 
    ? `Found <b>${filteredData.length}</b> ${isClothing ? 'outfits' : 'backgrounds'}`
    : `共找到 <b>${filteredData.length}</b> 款${isClothing ? '服饰' : '背景'}`;
  resultEl.innerHTML = resultText;
  
  if (filteredData.length === 0) {
    const noResultsTitle = state.displayLang === 'en' 
      ? `No matching ${isClothing ? 'outfits' : 'backgrounds'} found` 
      : `没有找到符合条件的${isClothing ? '服饰' : '背景'}`;
    const noResultsDesc = state.displayLang === 'en' 
      ? 'Try resetting your checkboxes or typing a different search query' 
      : '请尝试重置多选框或输入不同的搜索词';
    galleryEl.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
        <p style="font-size: 2rem; margin-bottom: 16px;">${isClothing ? '🌸' : '🌌'}</p>
        <h3 style="font-size: 1.2rem; font-weight:600; color: #fff; margin-bottom: 8px;">${noResultsTitle}</h3>
        <p style="font-size: 0.85rem;">${noResultsDesc}</p>
      </div>
    `;
    return;
  }

  galleryEl.innerHTML = filteredData.map(c => {
    const initial = (c.name_zh || c.name || '?').trim().charAt(0).toUpperCase() || '?';
    const hasImage = !!c.preview;
    
    // Shimmer placeholder
    const ph = `<div class="ph" style="--h:${c.id.slice(-3)}">
        <span>${esc(initial)}</span><em>awaiting render</em></div>`;
    const shot = hasImage
      ? `<img class="shot" loading="lazy" decoding="async"
              src="${esc(c.preview)}" alt="${esc(c.name)}"
              onerror="this.remove()">` : '';

    // Bilingual prompt tags rendering
    let promptTagsHtml = '';
    const enTags = c.tags ? c.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
    const zhTags = c.tags_zh ? c.tags_zh.split(',').map(t => t.trim()).filter(Boolean) : [];
    
    enTags.forEach((tag, idx) => {
      const zh = zhTags[idx] || '';
      const displayTag = (zh && state.displayLang === 'bilingual') ? `${tag} (${zh})` : tag;
      promptTagsHtml += `<span class="tag" data-en="${esc(tag)}">${esc(displayTag)}</span>`;
    });

    const copyLabel = state.displayLang === 'bilingual' ? '⧉ 复制/Copy' : '⧉ Copy';
    const overlayTitle = `Prompt Tags · ${enTags.length} <span style="font-size: 9px; font-weight: normal; margin-left: auto; background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; display: inline-flex; align-items: center; gap: 3px; border: 1px solid rgba(255,255,255,0.08);">${copyLabel}</span>`;

    const overlay = `
      <div class="ov-scroll" style="margin-bottom: 0; padding-bottom: 0;">
        <button class="ov-label-btn" data-copy="tags">${overlayTitle}</button>
        <div class="ov-tags">${promptTagsHtml}</div>
      </div>`;

    const displayNameZh = (c.name_zh && state.displayLang === 'bilingual') ? `<div class="name-zh" style="font-size: 0.9rem; font-weight: 700; color: #fff; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${esc(c.name_zh)}</div>` : '';
    const displayNameEn = state.displayLang === 'en'
      ? `<div class="name-en" style="font-size: 0.8rem; color: #fff; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${esc(c.name)}</div>`
      : `<div class="name-en" style="font-size: 0.72rem; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: normal;">${esc(c.name)}</div>`;
    
    const meta = `
      <div class="name-container" title="${esc(c.name_zh ? c.name_zh + ' / ' + c.name : c.name)}">
        ${displayNameZh}
        ${displayNameEn}
      </div>
    `;

    return `
      <article class="tile" data-id="${esc(c.id)}">
        <div class="thumb">
          ${ph}${shot}
          <div class="meta">${meta}</div>
          <div class="overlay">${overlay}</div>
        </div>
      </article>
    `;
  }).join('');

  bindCardEvents();
}

// Bind overlay copy actions
function bindCardEvents() {
  galleryEl.querySelectorAll('.tile').forEach(card => {
    const id = card.dataset.id;
    const data = state.mode === 'clothing' ? clothingData : backgroundData;
    const item = data.find(d => d.id === id);
    if (!item) return;

    // Copy full prompt
    const copyBtn = card.querySelector('.ov-label-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', e => {
        e.stopPropagation();
        copyText(item.tags, "已成功复制英文 Prompt！🌸");
      });
    }

    // Copy single tag click
    card.querySelectorAll('.tag').forEach(tagEl => {
      tagEl.addEventListener('click', e => {
        e.stopPropagation();
        const enText = tagEl.dataset.en;
        copyText(enText, `已复制标签: ${enText} 🌸`);
      });
    });
  });
}

// 9. Tab Switching Logic
function setupModeToggle() {
  if (!modeSwitcher) return;

  const buttons = modeSwitcher.querySelectorAll('.mode-btn');
  
  // 选项卡点击事件
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetMode = btn.dataset.mode;
      if (state.mode === targetMode) return;
      
      switchMode(targetMode);
    });
  });

  // 主标题点击彩蛋：点击标题也可以切换模式
  if (brandToggle) {
    brandToggle.addEventListener('click', (e) => {
      e.preventDefault();
      const nextMode = state.mode === 'clothing' ? 'background' : 'clothing';
      switchMode(nextMode);
    });
  }
}

function switchMode(targetMode) {
  state.mode = targetMode;
  
  // 1. 更新选项卡视觉激活态
  const buttons = modeSwitcher.querySelectorAll('.mode-btn');
  buttons.forEach(b => {
    if (b.dataset.mode === targetMode) {
      b.classList.add('active');
    } else {
      b.classList.remove('active');
    }
  });

  // 2. 清空当前的侧边栏筛选与搜索框，避免跨品类过滤器错乱
  state.filters.categories.clear();
  state.filters.folders.clear();
  state.filters.traits.clear();
  state.q = '';
  searchEl.value = '';
  
  // 3. 动态更新搜索框占位词
  searchEl.placeholder = targetMode === 'clothing' 
    ? "Search clothing or tags…" 
    : "Search background or tags…";

  // 4. 加载并更新视图数据
  loadData();
}

// 10. Event Setup
function setupEventListeners() {
  // Global Search input (Debounced)
  searchEl.addEventListener('input', debounce(e => {
    state.q = e.target.value;
    applyFiltersAndSort();
  }, 150));

  // Sort buttons
  const sortBtns = document.querySelectorAll('#sort button');
  sortBtns.forEach(btn => {
    btn.addEventListener('click', e => {
      sortBtns.forEach(b => b.classList.remove('on'));
      btn.classList.add('on');
      state.sort = btn.dataset.sort;
      applyFiltersAndSort();
    });
  });

  // Language display selector
  langSelect.addEventListener('change', e => {
    state.displayLang = e.target.value;
    renderFacets();
    applyFiltersAndSort();
  });

  // Reset all filters button
  clearBtn.addEventListener('click', () => {
    state.filters.categories.clear();
    state.filters.folders.clear();
    state.filters.traits.clear();
    renderFacets();
    applyFiltersAndSort();
  });

  // Mobile sidebar filter toggle
  const filtersToggleBtn = $('#filters-toggle');
  const sidebarEl = $('#sidebar');
  const sidebarCloseBtn = $('#sidebar-close');

  if (filtersToggleBtn && sidebarEl && sidebarCloseBtn) {
    filtersToggleBtn.addEventListener('click', () => {
      const expanded = filtersToggleBtn.getAttribute('aria-expanded') === 'true';
      filtersToggleBtn.setAttribute('aria-expanded', !expanded);
      sidebarEl.classList.toggle('open');
    });

    sidebarCloseBtn.addEventListener('click', () => {
      filtersToggleBtn.setAttribute('aria-expanded', 'false');
      sidebarEl.classList.remove('open');
    });
  }
}

// Launch AnimaTags
document.addEventListener("DOMContentLoaded", init);
