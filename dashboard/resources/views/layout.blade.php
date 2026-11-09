<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="csrf-token" content="{{ csrf_token() }}">
<title>@yield('title', 'CCTV Analitik')</title>
<style>
  :root {
    color-scheme: light;
    --bg: #f4f4f2; --surface-1: #fcfcfb; --border: #e3e2de;
    --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #6b6a65;
    --grid: #ebeae6; --series-1: #2a78d6; --series-2: #eb6834; --neutral: #a9a8a2;
    --accent: #2a78d6; --live: #d03b3b; --ok: #2f8a4a;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #111110; --surface-1: #1a1a19; --border: #2c2c2a;
      --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #8f8e88;
      --grid: #2a2a28; --series-1: #3987e5; --series-2: #d95926; --neutral: #6f6e69;
      --accent: #3987e5; --ok: #4caf6a;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text-primary);
         font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  header { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between;
           padding: 16px; max-width: 1280px; margin: 0 auto; }
  h1 { font-size: 18px; margin: 0; }
  h2 { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 0 0 10px;
       text-transform: uppercase; letter-spacing: .04em; }
  main { max-width: 1280px; margin: 0 auto; padding: 0 16px 32px; display: grid; gap: 16px; }
  nav { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  nav a, .link { color: var(--accent); text-decoration: none; background: none; border: 0; font: inherit; cursor: pointer; padding: 0; }
  .who { color: var(--text-muted); font-size: 12px; }
  .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px; min-width: 0; }
  .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
  .tiles { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
  .tile { background: var(--bg); border-radius: 8px; padding: 12px; }
  .tile .v { font-size: 26px; font-weight: 650; font-variant-numeric: tabular-nums; }
  .tile .l { color: var(--text-secondary); font-size: 12px; }
  .note { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
  .err { color: var(--live); }
  .ok { color: var(--ok); }
  table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { text-align: left; padding: 6px 4px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  th { color: var(--text-secondary); font-weight: 600; font-size: 12px; }
  label { display: grid; gap: 4px; font-size: 12px; color: var(--text-secondary); }
  input, select { font: inherit; color: var(--text-primary); background: var(--bg); border: 1px solid var(--border);
                  border-radius: 6px; padding: 8px 10px; min-width: 0; }
  .btn { font: inherit; border: 0; border-radius: 6px; padding: 8px 14px; background: var(--accent); color: #fff; cursor: pointer; }
  .btn.danger { background: var(--live); }
  .btn.small { padding: 5px 10px; font-size: 12px; }
</style>
@stack('head')
</head>
<body>
@auth
<header>
  <h1>CCTV Analitik Anonim</h1>
  <nav>
    <a href="{{ route('dashboard') }}">Dashboard</a>
    @can('admin')<a href="{{ route('users.index') }}">Kelola akun</a>@endcan
    <span class="who">{{ auth()->user()->name }} · {{ \App\Models\User::ROLES[auth()->user()->role] ?? auth()->user()->role }}</span>
    <form method="post" action="{{ route('logout') }}">@csrf<button class="link">Keluar</button></form>
  </nav>
</header>
@endauth
@yield('content')
@stack('scripts')
</body>
</html>
