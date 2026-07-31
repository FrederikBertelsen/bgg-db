// ==UserScript==
// @name        boardgamegeek.com recommender
// @namespace   Violentmonkey Scripts
// @icon        https://cf.geekdo-static.com/icons/touch-icon180.png
// @version     0.1.0
// @match       https://boardgamegeek.com/boardgame/*
// @grant       GM_xmlhttpRequest
// @connect     localhost
// @connect     bgg-recommender.15263748.xyz
// @author      https://github.com/FrederikBertelsen
// @description Inject recommendations from API into BGG game pages
// ==/UserScript==

(function() {
  'use strict';

  // Set this to your recommender API instance, e.g. 'https://example.com'.
  const API_BASE_URL = 'http://localhost:8443';
  const MIN_SIMILARY_SCORE = 0.4;
  const MIN_SIMILARITY_RATING = 6.5;

  let injectionData = null;

  function getGameIdFromUrl() {
    const m = location.pathname.match(/\/boardgame\/(\d+)/);
    return m ? m[1] : null;
  }

  function saveInjectionData(data) {
    injectionData = data;
    try {
      const target = (typeof unsafeWindow !== 'undefined') ? unsafeWindow : window;
      try { target.__BGG_RECOMMENDER_DATA = data; } catch (e) { /* fail quietly */ }
    } catch (e) {
      // fallback
      window.__BGG_RECOMMENDER_DATA = data;
    }
    console.info('[BGG Recommender] Saved injection data', data);
  }

  function createStyles() {
    const css = `
    .bgg-reco-wrap{border:1px solid #ddd;padding:12px;margin:12px 0;background:#fff}
    .bgg-reco-title{font-weight:700;margin-bottom:10px;font-size:16px}
    .bgg-reco-list{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;width:100%}
    .bgg-reco-card{width:100%;border:1px solid #eee;padding:12px;background:#fafafa;cursor:pointer;display:flex;gap:12px;align-items:flex-start;position:relative;color:inherit;text-decoration:none}
    .bgg-reco-card:link,.bgg-reco-card:visited,.bgg-reco-card:hover,.bgg-reco-card:active,.bgg-reco-card:focus{color:inherit;text-decoration:none}
    .bgg-reco-thumb-wrap{width:160px;height:120px;flex:0 0 160px;position:relative;border:1px solid #ddd;background:#fff;padding:4px;display:block}
    .bgg-reco-thumb{width:100%;height:100%;object-fit:contain;display:block}
    .bgg-reco-info{flex:1;min-width:0}
    .bgg-reco-name{font-size:17px;font-weight:700;margin:0 0 6px}
    .bgg-reco-meta{font-size:17px;color:#444;margin-bottom:6px;font-weight:600}
    .bgg-reco-small{font-size:16px;color:#666}
    .bgg-reco-players{color:#fff;background:none;padding:0;border-radius:0;display:block;font-weight:600;font-size:16px}
    .bgg-reco-desc{font-size:16px;color:#333;padding:14px 0}
    .bgg-reco-score{background:#f2f2f2;padding:3px 8px;border-radius:4px;margin-left:6px;font-weight:700}
    .bgg-reco-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
    .bgg-reco-tag{background:#eef2fa;padding:6px 10px;border-radius:14px;font-size:13px;color:#2b4d8a}
    .bgg-reco-stats{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px}
    .bgg-reco-stat{font-size:14px;color:#333}
    .bgg-reco-badge{position:absolute;top:10px;right:10px;color:#fff;padding:6px 10px;border-radius:14px;font-size:13px;font-weight:700;z-index:3;box-shadow:0 2px 6px rgba(0,0,0,0.12)}
    .bgg-reco-label{color:#666;font-weight:600}
    .bgg-reco-value{font-weight:700;color:#222}
    .bgg-reco-rating{color:#fff}
    .bgg-reco-players{font-size:16px;color:#333;margin-top:4px}
    .bgg-reco-polarization{font-size:16px;color:#333;margin-top:4px}
    .bgg-header-data-item{white-space:nowrap;display:block;color:#fff;font-weight:700}
    .bgg-header-data-label{color:#fff;font-weight:700}
    .bgg-header-data-box{padding:8px 10px;border:1px solid rgba(255,255,255,0.22);border-radius:8px;background:rgba(255,255,255,0.03)}
    .bgg-header-data-row{white-space:normal;display:block;color:#fff;font-weight:400;word-wrap:break-word;overflow-wrap:break-word}
    .bgg-player-score-chart{margin-top:6px;padding:8px 10px;border:1px solid rgba(255,255,255,0.22);border-radius:8px;background:rgba(255,255,255,0.03)}
    .bgg-player-score-chart-title{color:#fff;font-weight:700}
    .bgg-player-score-chart text{fill:#fff}
    .bgg-game-metadata{font-size:16px;color:#fff;margin-top:4px}
    .bgg-game-metadata .gameplay-item-primary{display:flex;flex-direction:column;gap:4px}
    .bgg-game-metadata .bgg-reco-label{color:#fff;font-weight:600}
    .bgg-game-metadata .bgg-reco-value{font-weight:700;color:#fff}
    `;
    const s = document.createElement('style');
    s.textContent = css;
    document.head.appendChild(s);
  }

  function buildChips(list) {
    if (!Array.isArray(list) || list.length === 0) return null;
    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.flexWrap = 'wrap';
    wrap.style.gap = '10px';
    list.forEach(v => {
      const el = document.createElement('div');
      el.style.background = '#eef2fa';
      el.style.padding = '6px 10px';
      el.style.borderRadius = '14px';
      el.style.fontSize = '13px';
      el.style.color = '#222';
      el.textContent = v;
      wrap.appendChild(el);
    });
    return wrap;
  }

  function buildPlayerCountChart(scores) {
    if (!scores || typeof scores !== 'object') return null;
    const entries = Object.entries(scores);
    if (entries.length === 0) return null;

    // Normalize order: keep insertion order from object
    const values = entries.map(([, v]) => Number(v) || 0);
    const labels = entries.map(([k]) => k);
    const maxVal = Math.max(...values, 0.0001);

    // Dynamically scale: wider container and tighter spacing for many bars
    const hasMany = labels.length > 20;
    const containerWidth = hasMany ? 500 : 300;
    const spacing = hasMany ? 3 : 6;
    const minBarWidth = 6;
    const barWidth = Math.max(minBarWidth, Math.floor((containerWidth - spacing * (labels.length + 1)) / labels.length));
    const width = Math.min(containerWidth, labels.length * (barWidth + spacing) + spacing);
    const height = 80;

    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height + 30);

    values.forEach((v, i) => {
      const h = Math.round((v / maxVal) * height);
      const x = i * (barWidth + spacing) + spacing;
      const y = height - h;

      const rect = document.createElementNS(svgNS, 'rect');
      rect.setAttribute('x', x);
      rect.setAttribute('y', y);
      rect.setAttribute('width', barWidth);
      rect.setAttribute('height', h);
      rect.setAttribute('fill', '#2b4d8a');
      svg.appendChild(rect);

      const lbl = document.createElementNS(svgNS, 'text');
      lbl.setAttribute('x', x + barWidth / 2);
      lbl.setAttribute('y', height + 14);
      lbl.setAttribute('font-size', '12');
      lbl.setAttribute('fill', '#444');
      lbl.setAttribute('text-anchor', 'middle');
      lbl.textContent = labels[i];
      svg.appendChild(lbl);
    });

    return svg;
  }

  function renderHeaderGameLists(data) {
    if (!data) return;

    const headerCredits = document.querySelector('div.game-header-credits.hidden-game-header-collapsed ul');
    if (!headerCredits) return;

    const box = document.createElement('li');
    box.className = 'bgg-header-data-box';

    const lists = [
      ['Niches', data.niches || []],
      ['Types', data.types || []],
      ['Themes', data.themes || []],
      ['Components', data.components || []],
      ['Mechanics', data.mechanics || []]
    ];

    lists.forEach(([label, arr]) => {
      const row = document.createElement('div');
      row.className = 'bgg-header-data-row';
      row.style.marginBottom = '10px';
      const labelSpan = document.createElement('span');
      labelSpan.className = 'bgg-header-data-label';
      labelSpan.textContent = `${label}: `;
      const valueSpan = document.createElement('span');
      valueSpan.className = 'bgg-header-data-value';
      valueSpan.textContent = (arr && arr.length) ? arr.join(' · ') : '';
      row.appendChild(labelSpan);
      row.appendChild(valueSpan);
      box.appendChild(row);
    });

    if (box.children.length) {
      headerCredits.insertBefore(box, headerCredits.firstChild);
    }
  }

  function renderPlayerCountScoreChart(data) {
    if (!data || !data.player_count_scores) return;

    const playersItem = document.querySelector('li[itemscope][itemprop="numberOfPlayers"]');
    if (!playersItem) return;

    if (data.player_count_scores && Object.keys(data.player_count_scores).length) {
      const chartWrap = document.createElement('div');
      chartWrap.className = 'bgg-player-score-chart';
      const chartTitle = document.createElement('div');
      chartTitle.className = 'bgg-player-score-chart-title';
      chartTitle.textContent = 'Player count scores';
      chartWrap.appendChild(chartTitle);
      const svg = buildPlayerCountChart(data.player_count_scores);
      if (svg) chartWrap.appendChild(svg);
      playersItem.appendChild(chartWrap);
    }
  }

  function renderGameVolumeWeight(data) {
    if (!data) return;

    const gameplay = document.querySelector('ul.gameplay');
    if (!gameplay) return;

    const li = document.createElement('li');
    li.className = 'gameplay-item bgg-game-metadata';

    const title = document.createElement('h3');
    title.className = 'sr-only';
    title.textContent = 'Estimated Volume and Weight';

    const primary = document.createElement('p');
    primary.className = 'gameplay-item-primary mb-0';

    const volumeRow = document.createElement('div');
    const volumeLabel = document.createElement('span');
    volumeLabel.className = 'bgg-reco-label';
    volumeLabel.textContent = 'Volume: ';
    const volumeValue = document.createElement('span');
    volumeValue.className = 'bgg-reco-value';
    volumeValue.textContent = data.estimated_volume_cm3 != null ? `${Number(data.estimated_volume_cm3).toFixed(2)} cm³` : 'N/A';
    volumeRow.appendChild(volumeLabel);
    volumeRow.appendChild(volumeValue);

    const weightRow = document.createElement('div');
    const weightLabel = document.createElement('span');
    weightLabel.className = 'bgg-reco-label';
    weightLabel.textContent = 'Weight: ';
    const weightValue = document.createElement('span');
    weightValue.className = 'bgg-reco-value';
    weightValue.textContent = data.estimated_weight_kg != null ? `${Number(data.estimated_weight_kg).toFixed(2)} kg` : 'N/A';
    weightRow.appendChild(weightLabel);
    weightRow.appendChild(weightValue);

    primary.appendChild(volumeRow);
    primary.appendChild(weightRow);

    li.appendChild(title);
    li.appendChild(primary);
    gameplay.appendChild(li);
  }

  function buildPolarizationSummary(polarization) {
    if (!polarization) return null;

    const div = document.createElement('div');
    div.className = 'bgg-reco-polarization';

    const label = document.createElement('span');
    label.className = 'bgg-reco-label';
    label.textContent = 'Polarization: ';

    const value = document.createElement('span');
    value.className = 'bgg-reco-value';
    const percentile = polarization.percentile != null ? `${Math.round(Number(polarization.percentile) * 100)}%` : 'N/A';
    value.textContent = `${polarization.label || 'Unknown'} (${percentile})`;

    div.appendChild(label);
    div.appendChild(value);
    return div;
  }

  function buildCard(item) {
    const a = document.createElement('a');
    a.href = `https://boardgamegeek.com/boardgame/${item.id}`;
    a.target = '_blank';
    a.rel = 'noopener';
    a.className = 'bgg-reco-card';

    const imgWrap = document.createElement('div');
    imgWrap.className = 'bgg-reco-thumb-wrap';

    const img = document.createElement('img');
    img.className = 'bgg-reco-thumb';
    img.src = item.thumbnail || '';
    img.alt = item.name;

    const info = document.createElement('div');
    info.className = 'bgg-reco-info';

    const name = document.createElement('div');
    name.className = 'bgg-reco-name';
    name.textContent = `${item.name} ${item.year_published ? `(${item.year_published})` : ''}`;

    // Stats line: rating, weight (similarity shown in badge)
    const statsLine = document.createElement('div');
    statsLine.className = 'bgg-reco-meta';

    const ratingLabel = document.createElement('span');
    ratingLabel.className = 'bgg-reco-rating';
    ratingLabel.textContent = 'Rating: ';
    const ratingValue = document.createElement('span');
    ratingValue.className = 'ng-binding bgg-reco-rating';
    const rating = item.rating != null ? Number(item.rating) : null;
    ratingValue.textContent = rating != null ? `★ ${rating.toFixed(2)}` : 'No rating';
    if (rating != null && isFinite(rating)) {
      ratingValue.classList.add(`has-rating-${Math.round(rating)}`);
    }

    const weightLabel = document.createElement('span');
    weightLabel.textContent = ' · Weight: ';
    const weightValue = document.createElement('span');
    weightValue.className = 'ng-binding';
    const weight = item.weight != null ? Number(item.weight) : null;
    weightValue.textContent = weight != null ? weight.toFixed(2) : 'N/A';
    if (weight != null && isFinite(weight)) {
      if (weight <= 3) weightValue.classList.add('gameplay-weight-light');
      else if (weight > 3 && weight <= 4) weightValue.classList.add('gameplay-weight-medium');
      else if (weight > 4) weightValue.classList.add('gameplay-weight-heavy');
    }

    statsLine.appendChild(ratingLabel);
    statsLine.appendChild(ratingValue);
    statsLine.appendChild(weightLabel);
    statsLine.appendChild(weightValue);

    // Players / Time
    const players = document.createElement('div');
    players.className = 'bgg-reco-players';

    const playersLabel = document.createElement('span');
    playersLabel.className = 'bgg-reco-label';
    playersLabel.textContent = 'Players: ';

    const playersValue = document.createElement('span');
    playersValue.className = 'bgg-reco-value';
    const minP = item.min_players != null ? item.min_players : '';
    const maxP = item.max_players != null ? item.max_players : '';
    playersValue.textContent = `${minP}${maxP ? '-' + maxP : ''}`;

    const timeSeparator = document.createElement('span');
    timeSeparator.textContent = ' · ';

    const timeLabel = document.createElement('span');
    timeLabel.className = 'bgg-reco-label';
    timeLabel.textContent = 'Time: ';

    const timeValue = document.createElement('span');
    timeValue.className = 'bgg-reco-value';
    const minT = item.min_playing_time != null ? item.min_playing_time : '';
    const maxT = item.max_playing_time != null ? item.max_playing_time : '';
    timeValue.textContent = `${minT}${maxT ? '-' + maxT + ' min' : ''}`;

    players.appendChild(playersLabel);
    players.appendChild(playersValue);
    players.appendChild(timeSeparator);
    players.appendChild(timeLabel);
    players.appendChild(timeValue);

    // Description
    const desc = document.createElement('div');
    desc.className = 'bgg-reco-desc';
    desc.textContent = item.short_description || '';

    // Ranks
    const ranksWrap = document.createElement('div');
    ranksWrap.className = 'bgg-reco-stats';
    if (Array.isArray(item.ranks) && item.ranks.length) {
      item.ranks.forEach(r => {
        const s = document.createElement('div');
        s.className = 'bgg-reco-stat';
        s.textContent = `${r.name}: ${r.value}`;
        ranksWrap.appendChild(s);
      });
    }

    // Niches
    const nichesWrap = document.createElement('div');
    nichesWrap.className = 'bgg-reco-tags';
    if (Array.isArray(item.niches) && item.niches.length) {
      item.niches.slice(0,6).forEach(n => {
        const t = document.createElement('div');
        t.className = 'bgg-reco-tag';
        t.textContent = n;
        nichesWrap.appendChild(t);
      });
    }

    // place ranks above the name as requested
    if (ranksWrap.children.length) info.appendChild(ranksWrap);
    info.appendChild(name);
    info.appendChild(statsLine);
    info.appendChild(players);
    const polarization = buildPolarizationSummary(item.polarization);
    if (polarization) info.appendChild(polarization);
    info.appendChild(desc);
    if (nichesWrap.children.length) info.appendChild(nichesWrap);

    // Similarity badge (inside thumbnail)
    if (item.score != null && isFinite(Number(item.score))) {
      const sim = document.createElement('div');
      sim.className = 'bgg-reco-badge';
      const percent = Math.round(Number(item.score) * 100);
      const badgeRating = Math.max(0, Math.min(10, Math.round(Number(item.score) * 10)));
      sim.classList.add(`has-rating-${badgeRating}`);
      sim.textContent = `${percent}%`;
      imgWrap.appendChild(sim);
    }

    imgWrap.appendChild(img);
    a.appendChild(imgWrap);
    a.appendChild(info);

    return a;
  }

  function renderRecommendations(parent, items) {
    const wrap = document.createElement('div');
    wrap.className = 'bgg-reco-wrap';

    const title = document.createElement('div');
    title.className = 'bgg-reco-title';
    title.textContent = 'Similar Games (Custom API)';

    wrap.appendChild(title);

    // If no recommendations, show a helpful message instead of cards
    if (!items || !items.length) {
      const msg = document.createElement('div');
      msg.style.fontSize = '14px';
      msg.style.color = '#444';
      msg.style.padding = '8px 0';
      msg.textContent = 'No recommendations found for this game.';
      wrap.appendChild(msg);
    } else {
      const list = document.createElement('div');
      list.className = 'bgg-reco-list';

      items.forEach(it => {
        const card = buildCard(it);
        list.appendChild(card);
      });

      wrap.appendChild(list);
    }

    // Attempt to insert between the two given ng-if elements
    const showAwards = parent.querySelector("[ng-if='geekitemctrl.showawards']");
    const expandDesc = parent.querySelector("[ng-if='geekitemctrl.expandabledescription']");

    if (expandDesc) {
      parent.insertBefore(wrap, expandDesc.nextSibling);
    } else if (showAwards && showAwards.nextSibling) {
      parent.insertBefore(wrap, showAwards.nextSibling);
    } else {
      parent.appendChild(wrap);
    }
  }

  function showError(parent, msg) {
    const e = document.createElement('div');
    e.style.color = 'red';
    e.style.margin = '8px 0';
    e.textContent = msg;
    parent.appendChild(e);
  }

  function fetchRecommendations(gameId, n = 10, parent) {
    const url = `${API_BASE_URL}/injection/${encodeURIComponent(gameId)}?min_score=${encodeURIComponent(MIN_SIMILARY_SCORE)}&min_rating=${encodeURIComponent(MIN_SIMILARITY_RATING)}`;
    console.info('[BGG Recommender] Fetching injection data', {
      gameId,
      minScore: MIN_SIMILARY_SCORE,
      minRating: MIN_SIMILARITY_RATING,
      url
    });
    GM_xmlhttpRequest({
      method: 'GET',
      url,
      onload(res) {
        console.info('[BGG Recommender] Response received', {
          status: res.status,
          statusText: res.statusText,
          responseLength: res.responseText.length
        });
        try {
          const data = JSON.parse(res.responseText);
          console.info('[BGG Recommender] Parsed response successfully');
          saveInjectionData(data);
          try { renderHeaderGameLists(data); } catch (e) { console.warn('[BGG Recommender] renderHeaderGameLists failed', e); }
          try { renderPlayerCountScoreChart(data); } catch (e) { console.warn('[BGG Recommender] renderPlayerCountScoreChart failed', e); }
          try { renderGameVolumeWeight(data); } catch (e) { console.warn('[BGG Recommender] renderGameVolumeWeight failed', e); }
          console.info('[BGG Recommender] About to render recommendations', {
            itemsCount: Array.isArray(data.recommendations) ? data.recommendations.length : 'not an array'
          });
          renderRecommendations(parent, data.recommendations || []);
        } catch (err) {
          console.error('[BGG Recommender] Failed parsing injection data', err);
          console.error('[BGG Recommender] Response text:', res.responseText);
          showError(parent, 'Failed to load recommendations (parse error)');
        }
      },
      onerror(err) {
        console.error('[BGG Recommender] Network request failed', err);
        showError(parent, 'Failed to load recommendations (network error)');
      }
    });
  }

  function init() {
    console.info('[BGG Recommender] Initializing');
    createStyles();

    if (!API_BASE_URL || !API_BASE_URL.trim()) {
      alert('BGG Recommender: Please set API_BASE_URL at the top of the userscript.');
      return;
    }

    const gameId = getGameIdFromUrl();
    if (!gameId) {
      console.info('[BGG Recommender] No game id found in URL');
      return;
    }
    const parent = document.querySelector('div.game-description');
    if (!parent) {
      console.info('[BGG Recommender] Could not find game description container');
      return;
    }
    console.info('[BGG Recommender] Loading game data', { gameId });
    fetchRecommendations(gameId, 10, parent);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
