#!/usr/bin/env node
/**
 * Used-car price scraper for cars.com (robust)
 * - Replaces ALL tokens ({year},{make},{model},{makeSlug},{modelSlug}) everywhere in template
 * - Stealth + networkidle waits + lazy scroll
 * - Price parsing: single/range, ignore "Call for price"
 * - Uniformity guard (skips suspicious uniform prices)
 * - Simple goto retry to avoid "frame detached"
 * - DEBUG=1 shows samples
 */

const fs = require('fs');
const path = require('path');
require('dotenv').config();

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

const { stringify } = require('csv-stringify/sync');

const DEBUG = process.env.DEBUG === '1';
const RATE_LIMIT_MS = Number(process.env.RATE_LIMIT_MS || 2500);
const HEADLESS = (process.env.HEADLESS || 'new');
const ZIP = process.env.ZIP || '94103';

function fileExists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function resolveData(...p) { return path.join(path.resolve(__dirname, '..', '..'), 'data', ...p); }

// ---------------- Config ----------------
let CFG = {
  urlTemplate: `https://www.cars.com/shopping/results/?stock_type=used&makes[]={makeSlug}&models[]={makeSlug}-{modelSlug}&year_min={year}&year_max={year}&maximum_distance=all&zip=${ZIP}`,
  minPrices: 12,
  minPrice: 1000,
  maxPrice: 300000,
  pageTimeoutMs: 60000,
  selectorCard: '.vehicle-card',
  selectorPriceCandidates: [
    '[data-test="vehicleCardPrice"]',
    '.primary-price',
    '[class*="price"]'
  ]
};
const localCfgPath = path.resolve(__dirname, 'scraper.config.js');
if (fileExists(localCfgPath)) {
  try { CFG = { ...CFG, ...(require(localCfgPath) || {}) }; }
  catch (e) { console.warn('⚠ failed to load scraper.config.js:', e.message); }
}

// ---------------- Helpers ----------------
const slug = s => String(s || '')
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+/g, '-').replace(/(^-|-$)/g, '');

const norm = s => String(s || '')
  .trim().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ')
  .replace(/\b(\w)/g, m => m.toUpperCase());

function parsePriceText(raw) {
  if (!raw) return NaN;
  const txt = String(raw).trim();
  if (/contact|call|no price|tbd|not priced|—|–|ask/i.test(txt)) return NaN;

  const range = txt.match(/\$?\s*([\d,.,]{4,8})\s*[–-]\s*\$?\s*([\d,.,]{4,8})/);
  if (range) {
    const a = Number(range[1].replace(/[,.]/g, ''));
    const b = Number(range[2].replace(/[,.]/g, ''));
    return (Number.isFinite(a) && Number.isFinite(b)) ? (a + b) / 2 : NaN;
    }

  const one = txt.match(/\$?\s*([\d,.,]{4,8})/);
  if (one) {
    const n = Number(one[1].replace(/[,.]/g, ''));
    return Number.isFinite(n) ? n : NaN;
  }
  return NaN;
}

function quantile(sorted, q) {
  if (!sorted.length) return NaN;
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  return (sorted[base + 1] !== undefined)
    ? sorted[base] + rest * (sorted[base + 1] - sorted[base])
    : sorted[base];
}

function stdev(a) {
  if (!a.length) return 0;
  const m = a.reduce((s, x) => s + x, 0) / a.length;
  const v = a.reduce((s, x) => s + (x - m) ** 2, 0) / a.length;
  return Math.sqrt(v);
}

// ---------------- Targets ----------------
function readTargets() {
  const p = resolveData('targets.csv');
  if (!fileExists(p)) { console.error(`❌ missing data/targets.csv`); process.exit(1); }
  const raw = fs.readFileSync(p, 'utf8').split(/\r?\n/);
  const rows = [];
  let headers = [];
  for (const lineRaw of raw) {
    const line = lineRaw.trim(); if (!line) continue;
    const parts = line.split(',');
    if (!headers.length) { headers = parts.map(h => h.trim()); continue; }
    const obj = {}; headers.forEach((h, i) => obj[h] = (parts[i] ?? '').trim());
    if (obj.year && obj.make && obj.model) rows.push(obj);
  }
  return rows;
}

// replace ALL occurrences of tokens in template
function replaceAll(str, find, repl) {
  return str.split(find).join(repl);
}

function buildUrl(year, make, model) {
  const makeSlug = slug(make);
  const modelSlug = slug(model);
  let t = String(CFG.urlTemplate);
  const repl = {
    '{year}': String(year),
    '{make}': String(make),
    '{model}': String(model),
    '{makeSlug}': makeSlug,
    '{modelSlug}': modelSlug
  };
  for (const [k, v] of Object.entries(repl)) {
    t = replaceAll(t, k, encodeURIComponent(v));
  }
  return t;
}

async function gotoWithRetry(browser, page, url, attempts = 2) {
  for (let i = 0; i < attempts; i++) {
    try {
      if (i > 0) {
        try { await page.close({ runBeforeUnload: false }); } catch {}
        page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 900 });
      }
      await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');
      await page.setCacheEnabled(false);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: CFG.pageTimeoutMs });
      // extra settle:
      await page.waitForNetworkIdle({ idleTime: 1000, timeout: 10000 }).catch(() => {});
      return page;
    } catch (e) {
      if (i === attempts - 1) throw e;
    }
  }
}

// ---------------- Scrape one target ----------------
async function scrapeOne(browser, page, target) {
  const { year, make, model } = target;
  const url = buildUrl(year, make, model);
  console.log(`[${make} ${model} ${year}] → ${url}`);

  try {
    page = await gotoWithRetry(browser, page, url, 2);
  } catch (e) {
    console.log('   ✗ error: failed to goto URL:', e.message);
    return { row: null, page };
  }

  try {
    await page.waitForSelector(CFG.selectorCard, { timeout: 45000 });
  } catch {
    const bodyTxt = (await page.content()).toLowerCase();
    if (bodyTxt.includes('no results') || bodyTxt.includes('try a different search')) {
      console.log('   ⚠ no results found, skipping');
      return { row: null, page };
    }
    if (bodyTxt.includes('are you a human') || bodyTxt.includes('captcha')) {
      console.log('   ⚠ captcha/bot wall detected, skipping');
      return { row: null, page };
    }
    console.log('   ✗ error: cards not found (timeout)');
    return { row: null, page };
  }

  try {
    await page.evaluate(async () => {
      let last = 0, same = 0;
      for (let i = 0; i < 12; i++) {
        window.scrollBy(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 900));
        const h = document.body.scrollHeight;
        if (h === last) { same++; if (same >= 2) break; } else { same = 0; }
        last = h;
      }
      window.scrollTo(0, 0);
    });
  } catch {}

  const rawPrices = await page.$$eval(CFG.selectorCard, (cards, sel) => {
    function pickPriceEl(card, selectors) {
      for (const s of selectors) {
        const el = card.querySelector(s);
        if (el && el.textContent && el.textContent.trim()) return el;
      }
      return null;
    }
    return cards.slice(0, 80).map(c => {
      const el = pickPriceEl(c, sel);
      return el ? el.textContent.trim() : '';
    });
  }, CFG.selectorPriceCandidates);

  const numbers = rawPrices
    .map(parsePriceText)
    .filter(n => Number.isFinite(n) && n >= CFG.minPrice && n <= CFG.maxPrice);

  if (DEBUG) {
    console.log('   rawPrices sample:', rawPrices.slice(0, 10));
    console.log('   parsed numbers sample:', numbers.slice(0, 10));
  }

  if (numbers.length < CFG.minPrices) {
    console.log(`   ⚠ collected ${numbers.length} prices (< minPrices), skipping aggregation`);
    return { row: null, page };
  }

  const uniqRounded = new Set(numbers.map(n => Math.round(n / 10) * 10));
  if (numbers.length >= 12 && (uniqRounded.size <= 2 || stdev(numbers) < 150)) {
    console.log('   ⚠ prices look too uniform; skipping aggregation (suspect selector/placeholder)');
    return { row: null, page };
  }

  numbers.sort((a, b) => a - b);
  const n = numbers.length;
  const median = quantile(numbers, 0.5);
  const p25 = quantile(numbers, 0.25);
  const p75 = quantile(numbers, 0.75);
  console.log(`   ✓ ${n} prices → median=${Math.round(median)}`);

  return {
    row: {
      year: String(year),
      make: norm(make),
      model: norm(model),
      median: Math.round(median),
      p25: Math.round(p25),
      p75: Math.round(p75),
      n,
      source: 'www.cars.com',
      ts: new Date().toISOString()
    },
    page
  };
}

// ---------------- Main ----------------
(async () => {
  const targets = readTargets();
  const TOTAL = targets.length;
  const OFFSET = Math.max(0, parseInt(process.env.OFFSET || '0', 10));
  const LIMIT = Math.max(0, parseInt(process.env.LIMIT || '20', 10));
  const end = Math.min(TOTAL, OFFSET + LIMIT);

  console.log(`Planning to scrape ${end - OFFSET} targets (OFFSET=${String(OFFSET).padStart(4)}, LIMIT=${LIMIT}).`);

  const browser = await puppeteer.launch({
    headless: HEADLESS,
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage','--disable-gpu','--window-size=1366,900']
  });
  let page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  const outPath = resolveData('scraped_used.csv');
  const rowsOut = [];

  for (let i = OFFSET; i < end; i++) {
    const t = targets[i];
    const pretty = `${t.year} ${t.make} ${t.model}`;
    console.log(`[${i - OFFSET + 1}/${end - OFFSET}] ${pretty}`);
    const res = await scrapeOne(browser, page, t);
    page = res.page;
    if (res.row) rowsOut.push(res.row);
    if (i < end - 1) await new Promise(r => setTimeout(r, RATE_LIMIT_MS));
  }

  await browser.close();

  if (!rowsOut.length) {
    console.log('⚠ no rows aggregated, nothing written');
    console.log(`Done. Started at: , finished at: ${new Date().toISOString()}`);
    process.exit(0);
  }

  const headerNeeded = !fileExists(outPath);
  const records = rowsOut.map(r => [r.year, r.make, r.model, r.median, r.p25, r.p75, r.n, r.source, r.ts]);
  const header = ['year','make','model','median','p25','p75','n','source','ts'];
  const csv = stringify(records, { header: headerNeeded, columns: header });
  fs.appendFileSync(outPath, csv);

  console.log(`✅ wrote ${rowsOut.length} ${rowsOut.length === 1 ? 'row' : 'rows'} to ${outPath}`);
  console.log(`Done. Started at: , finished at: ${new Date().toISOString()}`);
})().catch(err => { console.error(err); process.exit(1); });
