@extends('layout')
@section('title', 'Masuk · CCTV Analitik')
@section('content')
<main style="max-width: 380px; padding-top: 12vh">
  <form class="card" method="post" action="{{ route('login') }}" style="display: grid; gap: 12px">
    @csrf
    <h1>CCTV Analitik</h1>
    <label>Email <input type="email" name="email" value="{{ old('email') }}" required autofocus autocomplete="username"></label>
    <label>Password <input type="password" name="password" required autocomplete="current-password"></label>
    <label style="display: flex; gap: 6px; align-items: center"><input type="checkbox" name="remember" value="1"> Ingat saya</label>
    @error('email')<p class="err" style="margin: 0">{{ $message }}</p>@enderror
    @error('throttle')<p class="err" style="margin: 0">{{ $message }}</p>@enderror
    <button class="btn">Masuk</button>
  </form>
</main>
@endsection
