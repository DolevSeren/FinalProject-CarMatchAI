const fs = require("fs");
const path = require("path");
const { parse } = require("csv-parse/sync");
const { stringify } = require("csv-stringify/sync");
const puppeteer = require("puppeteer-extra");
const Stealth = require("puppeteer-extra-plugin-stealth");
require("dotenv").config();

puppeteer.use(Stealth());

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function quantile(sortedArr, q) {
  if (!sortedArr.length) return NaN;
  const pos = (sortedArr.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sortedArr[base + 1] !== undefined) {
    return sortedArr[base] + rest * (sortedArr[base + 1] - sortedArr[base]);
  } else {
    return sortedArr[base];
  }
}
function slug(s) {
  return String(s || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/(^-|-$)/g, "");
}

(async () => {
  const ROOT = path.resolve(__dirname, "..", "..");
  const dataDir = path.join(ROOT, "data");
  const targetsPath = path.join(dataDir, "targets.csv");
  const outPath = path.join(dataDir, "scraped_used.csv");

  if (!fs.existsSync(targetsPath)) {
    console.error("❌ data/targets.csv not found. Create it first.");
    process.exit(1);
  }

  const cfgPath = path.join(__dirname, "scraper.config.json");
  if (!fs.existsSync(cfgPath)) {
    console.error("❌ scraper.config.json not found.");
    process.exit(1);
  }
  const CFG = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
  const RATE_LIMIT_MS = parseInt(process.env.RATE_LIMIT_MS || CFG.rateLimitMs || "3500", 10);
  const OFFSET = parseInt(process.env.OFFSET || "0", 10);
  const LIMIT  = parseInt(process.env.LIMIT  || "0", 10); // 0 = no limit

  // טוענים יעדים
  const csv = fs.readFileSync(targetsPath, "utf8");
  let targets = parse(csv, { columns: true, skip_empty_lines: true });

  // טוענים קובץ פלט קיים כדי לדלג על שכבר נאסף, וגם כדי להוסיף/למזג
  /** @type {{year:string,make:string,model:string}[]} */
  let existing = [];
  if (fs.existsSync(outPath)) {
    try {
      const prev = fs.readFileSync(outPath, "utf8");
      existing = parse(prev, { columns: true, skip_empty_lines: true });
    } catch (e) {
      console.warn("⚠ could not read existing scraped_used.csv, proceeding fresh");
    }
  }
  const seen = new Set(existing.map(r => `${r.year}|${r.make}|${r.model}`));

  // דילוג על מה שכבר נאסף
  targets = targets.filter(t => {
    const k = `${t.year}|${t.make}|${t.model}`;
    return !seen.has(k);
  });

  // חלון OFFSET/LIMIT
  const start = Math.max(0, OFFSET);
  const end = LIMIT > 0 ? Math.min(targets.length, start + LIMIT) : targets.length;
  targets = targets.slice(start, end);

  console.log(`Planning to scrape ${targets.length} targets (OFFSET=${OFFSET}, LIMIT=${LIMIT}).`);

  const browser = await puppeteer.launch({
    headless: CFG.headless !== false,
    args: ["--no-sandbox","--disable-setuid-sandbox"]
  });
  const page = await browser.newPage();
  if (process.env.USER_AGENT) {
    await page.setUserAgent(process.env.USER_AGENT);
  }

  const rows = [];
  const startedAt = new Date().toISOString();

  for (let i = 0; i < targets.length; i++) {
    const t = targets[i];
    const make = String(t.make || "").trim();
    const model = String(t.model || "").trim();
    const year = String(t.year || "").trim();
    if (!make || !model || !year) continue;

    const makeSlug = slug(make);
    const modelSlug = slug(model);

    const url = CFG.urlTemplate
      .replace("{year}", encodeURIComponent(year))
      .replace("{make}", encodeURIComponent(make))
      .replace("{model}", encodeURIComponent(model))
      .replace("{makeSlug}", makeSlug)
      .replace("{modelSlug}", modelSlug);

    console.log(`[${i+1}/${targets.length}] ${year} ${make} ${model} → ${url}`);

    try {
      await page.goto(url, { waitUntil: "networkidle2", timeout: CFG.waitTimeoutMs || 30000 });
      if (CFG.preWaitSelector) {
        await page.waitForSelector(CFG.preWaitSelector, { timeout: CFG.waitTimeoutMs || 30000 });
      }

      // גלילה מתונה כדי לטעון lazy content
      await page.evaluate(async () => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        for (let i = 0; i < 12; i++) {
          window.scrollBy(0, 1200);
          await sleep(250);
        }
      });

      const prices = await page.$$eval(
        CFG.priceSelector,
        (nodes, attr, regexStr) => {
          const rx = regexStr ? new RegExp(regexStr, "gi") : null;
          const out = [];
          for (const n of nodes) {
            let raw = attr ? n.getAttribute(attr) || "" : (n.textContent || "");
            let s = String(raw);
            let picked = s;
            if (rx) {
              const m = s.match(rx);
              if (m && m[0]) picked = m[0];
            }
            const num = parseFloat(picked.replace(/[^0-9.]/g, ""));
            if (!Number.isNaN(num)) out.push(num);
          }
          return out;
        },
        CFG.priceAttr || null,
        CFG.priceRegex || null
      );

      const vals = (prices || []).filter(x => Number.isFinite(x)).sort((a,b) => a-b);
      const n = vals.length;
      if (n >= (CFG.minPrices || 5)) {
        const p25 = quantile(vals, 0.25);
        const med = quantile(vals, 0.5);
        const p75 = quantile(vals, 0.75);
        rows.push({
          year, make, model,
          price_used_p25: Math.round(p25),
          price_used_median: Math.round(med),
          price_used_p75: Math.round(p75),
          n_listings: n,
          source: `puppeteer:www.cars.com`,
          scraped_at: new Date().toISOString()
        });
        console.log(`   ✓ ${n} prices → median=${Math.round(med)}`);
      } else {
        console.log(`   ⚠ collected ${n} prices (< minPrices), skipping aggregation`);
      }
    } catch (err) {
      console.log(`   ✗ error: ${err && err.message ? err.message : err}`);
    }

    await sleep(RATE_LIMIT_MS);
  }

  // כותבים/ממזגים לפלט (דדופליקציה לפי year/make/model)
  let finalRows = rows;
  if (fs.existsSync(outPath)) {
    try {
      const prev = fs.readFileSync(outPath, "utf8");
      const prevRows = parse(prev, { columns: true, skip_empty_lines: true });
      const keyed = new Map(prevRows.map(r => [`${r.year}|${r.make}|${r.model}`, r]));
      for (const r of rows) keyed.set(`${r.year}|${r.make}|${r.model}`, r);
      finalRows = Array.from(keyed.values());
    } catch (e) {
      // אם כשל קריאה, נסתפק בשורות החדשות
    }
  }

  if (finalRows.length) {
    const csvOut = stringify(finalRows, { header: true });
    fs.writeFileSync(outPath, csvOut, "utf8");
    console.log(`✅ wrote ${rows.length} new rows (total ${finalRows.length}) to ${outPath}`);
  } else {
    console.log("⚠ no rows aggregated, nothing written");
  }

  await browser.close();
  console.log(`Done. Started at: ${startedAt}, finished at: ${new Date().toISOString()}`);
})();
