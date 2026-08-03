"""Offline self-contained review.html generator (no CDN / no network)."""

from __future__ import annotations

import html
import json
from typing import Any

from .contracts import ReviewError

# Browser payload must not embed storage paths or absolute URLs (offline contract).
_HTML_ASSET_KEYS = (
    "asset_id",
    "sha256",
    "byte_size",
    "mime_type",
    "detected_format",
    "width",
    "height",
    "reference_count",
    "product_count",
    "brand_count",
    "image_ids",
    "product_ids",
    "brands",
    "is_exact_duplicate_group",
    "is_cross_product_shared",
    "is_cross_brand_shared",
    "selection_segment",
    "selection_rank",
    "preview_filename",
    "thumb_filename",
    "watermark_prescreen",
    "watermark_review_required",
    "min_dimension",
    "max_dimension",
    "megapixels",
    "aspect_ratio",
    "alpha_present",
    "border_lightness_mean",
    "border_uniformity_score",
    "sharpness_score",
    "low_resolution_candidate",
    "extreme_aspect_candidate",
    "transparent_background_candidate",
    "busy_or_nonuniform_border_candidate",
)

_HTML_ASSIGNMENT_KEYS = (
    "assignment_id",
    "asset_id",
    "image_id",
    "product_id",
    "sku",
    "product_slug",
    "product_name",
    "brand_id",
    "brand_name",
    "category_id",
    "category_name",
    "is_primary",
    "display_order",
)

_FORBIDDEN_HTML_KEYS = frozenset(
    {"image_url", "source_relative_path", "mapped_local_relative_path"}
)


def _strip_urlish(value: Any) -> Any:
    if isinstance(value, str):
        low = value.lower()
        if "http://" in low or "https://" in low or low.startswith("//"):
            return ""
        return value
    if isinstance(value, list):
        return [_strip_urlish(v) for v in value]
    if isinstance(value, dict):
        return {
            k: _strip_urlish(v)
            for k, v in value.items()
            if k not in _FORBIDDEN_HTML_KEYS
        }
    return value


def html_safe_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for asset in assets:
        row = {k: asset.get(k) for k in _HTML_ASSET_KEYS if k in asset}
        out.append(_strip_urlish(row))
    return out


def html_safe_assignments(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for asg in assignments:
        row = {k: asg.get(k) for k in _HTML_ASSIGNMENT_KEYS if k in asg}
        out.append(_strip_urlish(row))
    return out


def assert_html_offline_contract(html_text: str) -> None:
    """Fail closed if the offline HTML embeds network or storage URL fields."""
    lowered = html_text.lower()
    if "http://" in lowered or "https://" in lowered:
        raise ReviewError("html", "review.html must not contain http(s) URL strings")
    if "//api" in lowered:
        raise ReviewError("html", "review.html must not contain //api host references")
    if '"image_url"' in html_text or "'image_url'" in html_text:
        raise ReviewError("html", "review.html must not embed image_url fields")
    if '"source_relative_path"' in html_text or "'source_relative_path'" in html_text:
        raise ReviewError("html", "review.html must not embed source_relative_path fields")


def _opt(values: list[str], selected: str) -> str:
    parts = []
    for v in values:
        sel = " selected" if v == selected else ""
        parts.append(f'<option value="{html.escape(v)}"{sel}>{html.escape(v)}</option>')
    return "".join(parts)


def build_review_html(
    *,
    batch_id: str,
    assets: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    schema: dict[str, Any],
) -> str:
    """Build a single-file offline review UI with embedded JSON payload."""
    safe_assets = html_safe_assets(assets)
    safe_assignments = html_safe_assignments(assignments)
    payload = {
        "review_schema_version": schema["review_schema_version"],
        "batch_id": batch_id,
        "assets": safe_assets,
        "assignments": safe_assignments,
        "schema": schema,
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Prevent accidental </script> breakouts
    payload_json = payload_json.replace("<", "\\u003c")

    asset_wm = schema["asset_level"]["watermark_status"]
    asset_dec = schema["asset_level"]["asset_decision"]
    # quality/background/crop/rights/suitability options are rendered from schema in JS
    _ = (
        schema["asset_level"]["quality_status"],
        schema["asset_level"]["background_status"],
        schema["asset_level"]["crop_status"],
        schema["asset_level"]["rights_status"],
        schema["assignment_level"]["suitability_status"],
        schema["assignment_level"]["assignment_decision"],
    )

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{html.escape(batch_id)} — بازبینی تصاویر موجود</title>
<style>
:root {{ --bg:#f6f4ef; --card:#fff; --ink:#1c1917; --muted:#57534e; --accent:#0f766e; --line:#d6d3d1; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Tahoma,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }}
header {{ padding:1rem 1.25rem; background:#134e4a; color:#ecfdf5; }}
header h1 {{ margin:0; font-size:1.15rem; }}
header p {{ margin:.35rem 0 0; opacity:.9; font-size:.9rem; }}
.layout {{ display:grid; grid-template-columns:280px 1fr; gap:0; min-height:calc(100vh - 88px); }}
aside {{ background:#fff; border-left:1px solid var(--line); padding:.75rem; overflow:auto; }}
main {{ padding:1rem 1.25rem 2rem; }}
.filters label {{ display:block; font-size:.8rem; color:var(--muted); margin-top:.5rem; }}
.filters select, .filters input {{ width:100%; margin-top:.2rem; padding:.35rem; }}
.list button {{ display:block; width:100%; text-align:right; margin:.25rem 0; padding:.45rem .5rem; border:1px solid var(--line); background:#fff; border-radius:6px; cursor:pointer; }}
.list button.active {{ border-color:var(--accent); background:#ccfbf1; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1rem; margin-bottom:1rem; }}
.meta {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:.5rem; font-size:.85rem; }}
.meta div {{ background:#fafaf9; padding:.4rem .5rem; border-radius:6px; }}
.thumbs {{ display:flex; gap:1rem; flex-wrap:wrap; align-items:flex-start; }}
.thumbs a img {{ max-width:220px; max-height:220px; border:1px solid var(--line); background:
  linear-gradient(45deg,#ddd 25%,transparent 25%),linear-gradient(-45deg,#ddd 25%,transparent 25%),
  linear-gradient(45deg,transparent 75%,#ddd 75%),linear-gradient(-45deg,transparent 75%,#ddd 75%);
  background-size:16px 16px; background-position:0 0,0 8px,8px -8px,-8px 0; }}
.flag {{ display:inline-block; padding:.15rem .4rem; border-radius:999px; background:#ffedd5; color:#9a3412; font-size:.75rem; margin-inline-end:.25rem; }}
table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
th, td {{ border-bottom:1px solid var(--line); padding:.4rem; text-align:right; vertical-align:top; }}
.nav {{ display:flex; gap:.5rem; margin-bottom:1rem; }}
.nav button, .toolbar button {{ padding:.45rem .8rem; border:1px solid var(--line); background:#fff; border-radius:6px; cursor:pointer; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:1rem; }}
.field {{ margin:.4rem 0; }}
.field label {{ display:block; font-size:.8rem; color:var(--muted); }}
.field select, .field textarea {{ width:100%; padding:.35rem; }}
.note {{ font-size:.8rem; color:var(--muted); }}
@media (max-width:900px) {{ .layout {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>بازبینی انسانی تصاویر موجود — {html.escape(batch_id)}</h1>
  <p>تصمیم‌های سطح دارایی و سطح انتساب جدا هستند. هیچ تصویری با این بسته حذف یا جایگزین نمی‌شود. داده فقط در مرورگر (localStorage) می‌ماند.</p>
</header>
<div class="layout">
  <aside>
    <div class="filters">
      <label>فیلتر وضعیت بازبینی
        <select id="fUnreviewed"><option value="all">همه</option><option value="unreviewed">فقط بازبینی‌نشده</option><option value="reviewed">بازبینی‌شده</option></select>
      </label>
      <label>اشتراک
        <select id="fShare"><option value="all">همه</option><option value="shared">اشتراکی</option><option value="singleton">تکی</option></select>
      </label>
      <label>وضوح پایین
        <select id="fLow"><option value="all">همه</option><option value="yes">نامزد وضوح پایین</option></select>
      </label>
      <label>واترمارک
        <select id="fWm"><option value="all">همه</option>{_opt(asset_wm, "all")}</select>
      </label>
      <label>تصمیم دارایی
        <select id="fDec"><option value="all">همه</option>{_opt(asset_dec, "all")}</select>
      </label>
      <label>برند
        <select id="fBrand"><option value="all">همه</option></select>
      </label>
    </div>
    <div class="list" id="assetList"></div>
  </aside>
  <main>
    <div class="toolbar">
      <button type="button" id="btnPrev">قبلی</button>
      <button type="button" id="btnNext">بعدی</button>
      <button type="button" id="btnExportAsset">خروجی asset-review.csv</button>
      <button type="button" id="btnExportAsg">خروجی assignment-review.csv</button>
      <button type="button" id="btnExportState">خروجی review-state.json</button>
      <button type="button" id="btnImportState">ورود review-state.json</button>
      <input type="file" id="importFile" accept="application/json,.json" hidden/>
    </div>
    <div id="detail"></div>
  </main>
</div>
<script id="payload" type="application/json">{payload_json}</script>
<script>
(function() {{
  const DATA = JSON.parse(document.getElementById('payload').textContent);
  const LS_KEY = 'karzar-img-review:' + DATA.batch_id;
  const schema = DATA.schema;
  let state = loadState();
  let filteredIds = DATA.assets.map(a => a.asset_id);
  let idx = 0;

  function loadState() {{
    try {{
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return emptyState();
      const parsed = JSON.parse(raw);
      if (parsed.review_schema_version !== DATA.review_schema_version) return emptyState();
      return parsed;
    }} catch (e) {{ return emptyState(); }}
  }}
  function emptyState() {{
    const assets = {{}};
    const assignments = {{}};
    DATA.assets.forEach(a => {{
      assets[a.asset_id] = Object.assign({{}}, schema.asset_level.defaults, {{asset_id: a.asset_id}});
    }});
    DATA.assignments.forEach(x => {{
      assignments[x.assignment_id] = Object.assign({{}}, schema.assignment_level.defaults, {{
        assignment_id: x.assignment_id, asset_id: x.asset_id, image_id: x.image_id, product_id: x.product_id
      }});
    }});
    return {{ review_schema_version: DATA.review_schema_version, batch_id: DATA.batch_id, assets, assignments }};
  }}
  function save() {{ localStorage.setItem(LS_KEY, JSON.stringify(state)); }}

  const brandSet = new Set();
  DATA.assets.forEach(a => (a.brands || []).forEach(b => brandSet.add(b)));
  const brandSel = document.getElementById('fBrand');
  Array.from(brandSet).sort().forEach(b => {{
    const o = document.createElement('option'); o.value = b; o.textContent = b; brandSel.appendChild(o);
  }});

  function isAssetReviewed(id) {{
    const r = state.assets[id];
    if (!r) return false;
    return r.asset_decision !== 'UNREVIEWED' || r.watermark_status !== 'unreviewed' || (r.asset_notes || '').trim() !== '';
  }}

  function applyFilters() {{
    const u = document.getElementById('fUnreviewed').value;
    const sh = document.getElementById('fShare').value;
    const low = document.getElementById('fLow').value;
    const wm = document.getElementById('fWm').value;
    const dec = document.getElementById('fDec').value;
    const brand = document.getElementById('fBrand').value;
    filteredIds = DATA.assets.filter(a => {{
      if (sh === 'shared' && !a.is_cross_product_shared) return false;
      if (sh === 'singleton' && a.is_cross_product_shared) return false;
      if (low === 'yes' && !a.low_resolution_candidate) return false;
      const rev = state.assets[a.asset_id] || {{}};
      if (wm !== 'all' && (rev.watermark_status || 'unreviewed') !== wm) return false;
      if (dec !== 'all' && (rev.asset_decision || 'UNREVIEWED') !== dec) return false;
      if (brand !== 'all' && !(a.brands || []).includes(brand)) return false;
      if (u === 'unreviewed' && isAssetReviewed(a.asset_id)) return false;
      if (u === 'reviewed' && !isAssetReviewed(a.asset_id)) return false;
      return true;
    }}).map(a => a.asset_id);
    if (idx >= filteredIds.length) idx = 0;
    renderList();
    renderDetail();
  }}

  function renderList() {{
    const box = document.getElementById('assetList');
    box.innerHTML = '';
    filteredIds.forEach((id, i) => {{
      const a = DATA.assets.find(x => x.asset_id === id);
      const b = document.createElement('button');
      b.type = 'button';
      b.className = i === idx ? 'active' : '';
      b.textContent = (a.selection_segment || '') + ' · ' + id.slice(0, 12) + '… · p' + a.product_count;
      b.onclick = () => {{ idx = i; renderList(); renderDetail(); }};
      box.appendChild(b);
    }});
  }}

  function selectOpts(values, current) {{
    return values.map(v => '<option value="' + v + '"' + (v === current ? ' selected' : '') + '>' + v + '</option>').join('');
  }}

  function renderDetail() {{
    const el = document.getElementById('detail');
    if (!filteredIds.length) {{ el.innerHTML = '<p class="note">موردی با این فیلتر نیست.</p>'; return; }}
    const id = filteredIds[idx];
    const a = DATA.assets.find(x => x.asset_id === id);
    const rev = state.assets[id];
    const asgs = DATA.assignments.filter(x => x.asset_id === id);
    const flags = [];
    if (a.low_resolution_candidate) flags.push('وضوح پایین');
    if (a.extreme_aspect_candidate) flags.push('نسبت افراطی');
    if (a.transparent_background_candidate) flags.push('شفافیت');
    if (a.busy_or_nonuniform_border_candidate) flags.push('حاشیه شلوغ');
    el.innerHTML = `
      <div class="card">
        <div class="nav">
          <strong>دارایی ${{idx+1}} / ${{filteredIds.length}}</strong>
          <span class="note">${{a.asset_id}}</span>
        </div>
        <div class="thumbs">
          <a href="previews/${{a.preview_filename}}" target="_blank" rel="noopener">
            <img src="thumbs/${{a.thumb_filename}}" alt="thumbnail generated review derivative"/>
          </a>
          <div>
            <p class="note">تصویر بندانگشتی یک مشتق بازبینی است؛ واترمارک حذف نشده است.</p>
            <div>${{flags.map(f => '<span class="flag">'+f+'</span>').join('')}}</div>
          </div>
        </div>
        <div class="meta">
          <div>ابعاد: ${{a.width}}×${{a.height}}</div>
          <div>حجم: ${{a.byte_size}}</div>
          <div>محصولات: ${{a.product_count}}</div>
          <div>ارجاع‌ها: ${{a.reference_count}}</div>
          <div>برندها: ${{(a.brands||[]).join('، ') || '—'}}</div>
          <div>سگمنت: ${{a.selection_segment}}</div>
          <div>MP: ${{a.megapixels}}</div>
          <div>نسبت: ${{a.aspect_ratio}}</div>
        </div>
        <h3>بازبینی سطح دارایی</h3>
        <div class="field"><label>واترمارک</label><select data-asset="${{id}}" data-k="watermark_status">${{selectOpts(schema.asset_level.watermark_status, rev.watermark_status)}}</select></div>
        <div class="field"><label>کیفیت</label><select data-asset="${{id}}" data-k="quality_status">${{selectOpts(schema.asset_level.quality_status, rev.quality_status)}}</select></div>
        <div class="field"><label>پس‌زمینه</label><select data-asset="${{id}}" data-k="background_status">${{selectOpts(schema.asset_level.background_status, rev.background_status)}}</select></div>
        <div class="field"><label>کراپ/جهت</label><select data-asset="${{id}}" data-k="crop_status">${{selectOpts(schema.asset_level.crop_status, rev.crop_status)}}</select></div>
        <div class="field"><label>تصمیم دارایی</label><select data-asset="${{id}}" data-k="asset_decision">${{selectOpts(schema.asset_level.asset_decision, rev.asset_decision)}}</select></div>
        <div class="field"><label>حقوق/مجوز (جدا از واترمارک)</label><select data-asset="${{id}}" data-k="rights_status">${{selectOpts(schema.asset_level.rights_status, rev.rights_status)}}</select></div>
        <div class="field"><label>یادداشت دارایی</label><textarea data-asset="${{id}}" data-k="asset_notes" rows="2">${{escapeHtml(rev.asset_notes || '')}}</textarea></div>
      </div>
      <div class="card">
        <h3>بازبینی سطح انتساب محصول</h3>
        <table>
          <thead><tr><th>محصول</th><th>SKU</th><th>برند</th><th>دسته</th><th>IDs</th><th>تناسب</th><th>تصمیم</th><th>یادداشت</th></tr></thead>
          <tbody>
            ${{asgs.map(x => {{
              const r = state.assignments[x.assignment_id];
              return `<tr>
                <td>${{escapeHtml(x.product_name || '')}}</td>
                <td>${{escapeHtml(x.sku || '')}}</td>
                <td>${{escapeHtml(x.brand_name || '')}}</td>
                <td>${{escapeHtml(x.category_name || '')}}</td>
                <td>P${{x.product_id}} / I${{x.image_id}}</td>
                <td><select data-asg="${{x.assignment_id}}" data-k="suitability_status">${{selectOpts(schema.assignment_level.suitability_status, r.suitability_status)}}</select></td>
                <td><select data-asg="${{x.assignment_id}}" data-k="assignment_decision">${{selectOpts(schema.assignment_level.assignment_decision, r.assignment_decision)}}</select></td>
                <td><textarea data-asg="${{x.assignment_id}}" data-k="assignment_notes" rows="1">${{escapeHtml(r.assignment_notes || '')}}</textarea></td>
              </tr>`;
            }}).join('')}}
          </tbody>
        </table>
      </div>`;
    el.querySelectorAll('[data-asset]').forEach(node => {{
      node.addEventListener('change', onAssetChange);
      node.addEventListener('input', onAssetChange);
    }});
    el.querySelectorAll('[data-asg]').forEach(node => {{
      node.addEventListener('change', onAsgChange);
      node.addEventListener('input', onAsgChange);
    }});
  }}

  function escapeHtml(s) {{
    return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
  }}
  function onAssetChange(ev) {{
    const id = ev.target.getAttribute('data-asset');
    const k = ev.target.getAttribute('data-k');
    state.assets[id][k] = ev.target.value;
    save();
  }}
  function onAsgChange(ev) {{
    const id = ev.target.getAttribute('data-asg');
    const k = ev.target.getAttribute('data-k');
    state.assignments[id][k] = ev.target.value;
    save();
  }}

  function csvEscape(v) {{
    const s = String(v ?? '');
    if (/[",\\n\\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }}
  function download(name, text, type) {{
    const blob = new Blob([text], {{type: type || 'text/plain;charset=utf-8'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  }}
  function exportAssetCsv() {{
    const fields = ['review_schema_version','batch_id','asset_id','watermark_status','quality_status','background_status','crop_status','asset_decision','rights_status','asset_notes'];
    const lines = [fields.join(',')];
    DATA.assets.forEach(a => {{
      const r = state.assets[a.asset_id];
      lines.push(fields.map(f => csvEscape(f === 'review_schema_version' ? DATA.review_schema_version : f === 'batch_id' ? DATA.batch_id : r[f])).join(','));
    }});
    download('asset-review.csv', lines.join('\\n'), 'text/csv;charset=utf-8');
  }}
  function exportAsgCsv() {{
    const fields = ['review_schema_version','batch_id','assignment_id','asset_id','image_id','product_id','suitability_status','assignment_decision','assignment_notes'];
    const lines = [fields.join(',')];
    DATA.assignments.forEach(x => {{
      const r = state.assignments[x.assignment_id];
      lines.push(fields.map(f => csvEscape(f === 'review_schema_version' ? DATA.review_schema_version : f === 'batch_id' ? DATA.batch_id : r[f])).join(','));
    }});
    download('assignment-review.csv', lines.join('\\n'), 'text/csv;charset=utf-8');
  }}

  document.getElementById('btnPrev').onclick = () => {{ if (!filteredIds.length) return; idx = (idx - 1 + filteredIds.length) % filteredIds.length; renderList(); renderDetail(); }};
  document.getElementById('btnNext').onclick = () => {{ if (!filteredIds.length) return; idx = (idx + 1) % filteredIds.length; renderList(); renderDetail(); }};
  document.getElementById('btnExportAsset').onclick = exportAssetCsv;
  document.getElementById('btnExportAsg').onclick = exportAsgCsv;
  document.getElementById('btnExportState').onclick = () => download('review-state.json', JSON.stringify(state, null, 2), 'application/json');
  document.getElementById('btnImportState').onclick = () => document.getElementById('importFile').click();
  document.getElementById('importFile').onchange = (ev) => {{
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {{
      try {{
        const parsed = JSON.parse(String(reader.result));
        if (parsed.review_schema_version !== DATA.review_schema_version) throw new Error('schema');
        if (parsed.batch_id !== DATA.batch_id) throw new Error('batch');
        state = parsed; save(); applyFilters();
      }} catch (e) {{ alert('ورود وضعیت نامعتبر است'); }}
    }};
    reader.readAsText(file, 'utf-8');
  }};
  ['fUnreviewed','fShare','fLow','fWm','fDec','fBrand'].forEach(id => document.getElementById(id).addEventListener('change', applyFilters));
  applyFilters();
}})();
</script>
</body>
</html>
"""
