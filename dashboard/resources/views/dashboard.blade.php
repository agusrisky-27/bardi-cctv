@extends('layout')
@section('title', 'Dashboard · CCTV Analitik')
@push('head')
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  .live { display: grid; gap: 16px; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); }
  @media (max-width: 800px) { .live { grid-template-columns: 1fr; } }
  .video { width: 100%; aspect-ratio: 16 / 9; background: #000; border-radius: 8px; object-fit: contain; display: block; }
  .novideo { aspect-ratio: 16 / 9; display: grid; place-items: center; text-align: center; padding: 16px;
             border: 1px dashed var(--border); border-radius: 8px; color: var(--text-muted); }
  .tabs { display: flex; gap: 4px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 3px; width: fit-content; }
  .tabs button { border: 0; background: none; color: var(--text-secondary); padding: 6px 12px; border-radius: 6px; font: inherit; cursor: pointer; }
  .tabs button[aria-pressed="true"] { background: var(--accent); color: #fff; }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--neutral); margin-right: 6px; }
  .dot.on { background: var(--live); }
  .chart { position: relative; height: 240px; }
  .heat { width: 100%; border-radius: 8px; display: block; }
</style>
@endpush
@section('content')
<main>
  <div class="tabs" role="group" aria-label="Rentang waktu">
    @foreach ($ranges as $key => $label)
      <button data-range="{{ $key }}" aria-pressed="{{ $loop->first ? 'true' : 'false' }}">{{ $label }}</button>
    @endforeach
  </div>

  <section class="live">
    <div class="card">
      <h2><span class="dot" id="live_dot"></span>Live CCTV</h2>
      <div id="video_box" class="novideo">
        {{ $engineUrl ? 'Menunggu mesin analitik (python -m rcis.cli --rtsp --web)…' : 'Video live belum diatur: isi RCIS_ENGINE_URL di .env Laravel.' }}
      </div>
    </div>
    <div class="card">
      <h2>Saat ini</h2>
      <div class="tiles">
        <div class="tile"><div class="v" id="people_now">-</div><div class="l">Orang di ruangan</div></div>
        <div class="tile"><div class="v" id="laptop_now">-</div><div class="l">Pakai laptop</div></div>
        <div class="tile"><div class="v" id="door_live">-</div><div class="l">Masuk / keluar (sesi ini)</div></div>
      </div>
      <p class="note" id="live_note">Mesin analitik belum mengirim data.</p>
    </div>
  </section>

  <section class="card">
    <h2 id="range_title">Ringkasan</h2>
    <div class="tiles">
      <div class="tile"><div class="v" id="visitors">-</div><div class="l">Kunjungan (orang masuk)</div></div>
      <div class="tile"><div class="v" id="peak_people">-</div><div class="l">Maks. orang bersamaan</div></div>
      <div class="tile"><div class="v" id="avg_dwell">-</div><div class="l">Rata-rata lama di ruangan</div></div>
      <div class="tile"><div class="v" id="door_in">-</div><div class="l">Lewat pintu (masuk / keluar)</div></div>
      <div class="tile"><div class="v" id="laptop_total">-</div><div class="l">Total pakai laptop</div></div>
      <div class="tile" id="food_tile" hidden><div class="v" id="food_wait">-</div><div class="l">Rata-rata tunggu makanan</div></div>
    </div>
    <p class="note">Orang yang keluar lalu masuk lagi dihitung sebagai kunjungan baru, karena sistem tidak mengenali identitas.</p>
    <p class="note err" id="error" hidden></p>
  </section>

  <section class="grid">
    <div class="card"><h2 id="series_title">Kunjungan per jam</h2><div class="chart"><canvas id="c_series"></canvas></div></div>
    <div class="card">
      <h2>Laki-laki / perempuan</h2>
      <div class="chart" style="height:160px"><canvas id="c_gender"></canvas></div>
      <p class="note">Estimasi statistik dari model, akurasi terbatas. Tidak mengidentifikasi siapa pun.</p>
    </div>
    <div class="card"><h2>Arah datang</h2><div class="chart" style="height:200px"><canvas id="c_sides"></canvas></div></div>
    <div class="card"><h2>Area paling lama ditempati (menit)</h2><div class="chart"><canvas id="c_zones"></canvas></div></div>
    <div class="card">
      <h2>Durasi pakai laptop per orang</h2>
      <table><thead><tr><th>ID sementara</th><th>Mulai</th><th>Sesi</th><th>Durasi</th></tr></thead>
        <tbody id="laptop_rows"><tr><td colspan="4">-</td></tr></tbody></table>
      <p class="note">ID hanya nomor tracking sementara, tidak terhubung ke identitas.</p>
    </div>
    <div class="card">
      <h2>Log alert keamanan</h2>
      <table><thead><tr><th>Waktu</th><th>Jenis</th><th>Zona</th><th>Foto (wajah diburamkan)</th></tr></thead>
        <tbody id="alert_rows"><tr><td colspan="4">-</td></tr></tbody></table>
    </div>
    @if ($engineUrl)
      <div class="card"><h2>Heatmap posisi</h2><div id="heat_box" class="note">Heatmap belum ada.</div></div>
    @endif
  </section>
</main>
@endsection
@push('scripts')
<script>
const ENGINE = @json($engineUrl);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmtDur = s => s == null ? '-' : s < 60 ? `${Math.round(s)} dtk` : s < 3600 ? `${(s / 60).toFixed(1)} mnt` : `${(s / 3600).toFixed(1)} jam`;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const SIDE = {kiri: 'Kiri', kanan: 'Kanan', depan: 'Depan', belakang: 'Belakang'};
const ALERT = {restricted_zone: 'Zona terlarang', loitering: 'Berdiam terlalu lama', after_hours: 'Di luar jam operasional'};
const TITLES = @json($ranges);
let range = 'today';
const charts = {};

function barChart(id, labels, values, opts = {}) {
  const cfg = {
    type: 'bar',
    data: {labels, datasets: [{data: values, backgroundColor: opts.colors || css('--series-1'), borderRadius: 4,
                               borderSkipped: 'start', maxBarThickness: 28}]},
    options: {
      indexAxis: opts.horizontal ? 'y' : 'x', maintainAspectRatio: false, animation: false,
      plugins: {legend: {display: false},
                tooltip: {callbacks: {label: c => opts.fmt ? opts.fmt(c.parsed[opts.horizontal ? 'x' : 'y']) : `${c.formattedValue}`}}},
      scales: {
        x: {grid: {display: !!opts.horizontal, color: css('--grid')}, ticks: {color: css('--text-secondary')}, beginAtZero: true},
        y: {grid: {display: !opts.horizontal, color: css('--grid')}, ticks: {color: css('--text-secondary'), precision: 0}, beginAtZero: true},
      },
    },
  };
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), cfg);
}

// Build <img> only when there is a real URL; fall back to text if it fails to load.
function showImage(boxId, url, cls, alt, fallback, immediate = false) {
  const box = document.getElementById(boxId);
  if (!box) return;
  const img = new Image();
  img.className = cls; img.alt = alt;
  img.onload = () => box.replaceChildren(img);
  img.onerror = () => { box.className = 'novideo'; box.textContent = fallback; };
  img.src = url;
  if (immediate) box.replaceChildren(img);  // MJPEG streams may never fire onload
}

async function getJSON(url) {
  const r = await fetch(url, {cache: 'no-store', headers: {Accept: 'application/json'}});
  if (r.status === 401 || r.redirected) { location.reload(); throw new Error('sesi habis'); }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).message || r.statusText);
  return r.json();
}

async function loadStats() {
  const err = document.getElementById('error');
  try {
    const s = await getJSON(`{{ route('stats') }}?range=${range}`);
    err.hidden = true;
    document.getElementById('range_title').textContent = `Ringkasan · ${TITLES[range]}`;
    document.getElementById('visitors').textContent = s.visitors;
    document.getElementById('peak_people').textContent = s.peak_people;
    document.getElementById('avg_dwell').textContent = fmtDur(s.visitors ? s.avg_dwell_seconds : null);
    document.getElementById('door_in').textContent = `${s.door.in || 0} / ${s.door.out || 0}`;
    document.getElementById('laptop_total').textContent = fmtDur(s.laptop.total_seconds);
    document.getElementById('food_wait').textContent = fmtDur(s.avg_food_wait_seconds);
    document.getElementById('food_tile').hidden = s.avg_food_wait_seconds == null;  // office: no food data

    const hourly = s.bucket === 'hour';
    document.getElementById('series_title').textContent = hourly ? 'Kunjungan per jam' : 'Kunjungan per hari';
    barChart('c_series', s.series.labels.map(l => hourly ? `${l}:00` : l.slice(5)), s.series.values);

    const g = s.gender, total = g.male + g.female + g.unknown;
    const pct = n => total ? ` (${Math.round(100 * n / total)}%)` : '';
    barChart('c_gender', [`Laki-laki${pct(g.male)}`, `Perempuan${pct(g.female)}`, `Tidak diketahui${pct(g.unknown)}`],
             [g.male, g.female, g.unknown], {horizontal: true, colors: [css('--series-1'), css('--series-2'), css('--neutral')]});

    const sides = Object.keys(SIDE);
    barChart('c_sides', sides.map(k => SIDE[k]), sides.map(k => s.entry_sides[k] || 0), {horizontal: true});
    barChart('c_zones', s.zones.map(z => z.zone), s.zones.map(z => +(z.total_seconds / 60).toFixed(1)),
             {horizontal: true, fmt: v => `${v} menit`});

    const when = t => esc(String(t).slice(5, 16).replace('T', ' '));
    document.getElementById('laptop_rows').innerHTML = s.laptop.per_person.map(p =>
      `<tr><td>#${esc(p.track_id)}</td><td>${when(p.first_at)}</td><td>${esc(p.sessions)}</td><td>${fmtDur(p.seconds)}</td></tr>`).join('')
      || '<tr><td colspan="4">Belum ada data</td></tr>';
    document.getElementById('alert_rows').innerHTML = s.alerts.map(a =>
      `<tr><td>${when(a.at)}</td><td>${esc(ALERT[a.type] || a.type)}</td><td>${esc(a.zone || '-')}</td>` +
      `<td>${a.snapshot && ENGINE ? `<a href="${esc(ENGINE)}/alert-snapshot/${encodeURIComponent(a.snapshot)}" target="_blank" rel="noopener">lihat</a>` : '-'}</td></tr>`).join('')
      || '<tr><td colspan="4">Tidak ada alert</td></tr>';
    if (ENGINE) showImage('heat_box', `${ENGINE}/heatmap.png?t=${Date.now()}`, 'heat', 'Heatmap area yang paling sering ditempati', 'Heatmap belum ada.');
  } catch (e) {
    err.textContent = `Gagal memuat statistik: ${e.message}`;
    err.hidden = false;
  }
}

async function loadLive() {
  try {
    const l = await getJSON(`{{ route('live') }}`);
    document.getElementById('live_dot').classList.toggle('on', l.available);
    document.getElementById('live_note').textContent = l.available
      ? (l.fps ? `Kecepatan analisis: ${l.fps.toFixed(1)} FPS` : 'Mesin analitik aktif.')
      : (l.updated_at ? `Mesin analitik mati sejak ${String(l.updated_at).slice(0, 16).replace('T', ' ')}.` : 'Mesin analitik belum mengirim data.');
    for (const k of ['people_now', 'laptop_now']) document.getElementById(k).textContent = l.available ? l[k] : '-';
    document.getElementById('door_live').textContent = l.available ? `${l.count_in ?? 0} / ${l.count_out ?? 0}` : '-';
    if (l.available && ENGINE && !document.querySelector('#video_box img')) {
      document.getElementById('video_box').className = '';
      showImage('video_box', `${ENGINE}/video`, 'video', 'Video live dengan kotak deteksi', 'Video live tidak bisa dibuka dari perangkat ini.', true);
    }
  } catch (e) { /* engine or server restarting: try again next tick */ }
}

document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => {
  range = b.dataset.range;
  document.querySelectorAll('.tabs button').forEach(x => x.setAttribute('aria-pressed', x === b));
  loadStats();
}));
loadStats(); loadLive();
setInterval(loadStats, 15000);
setInterval(loadLive, 3000);
</script>
@endpush
