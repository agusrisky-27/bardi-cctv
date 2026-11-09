@extends('layout')
@section('title', 'Kelola akun · CCTV Analitik')
@section('content')
<main>
  @if (session('status'))<p class="ok">{{ session('status') }}</p>@endif
  @if ($errors->any())<p class="err">{{ $errors->first() }}</p>@endif

  <section class="card">
    <h2>Tambah akun</h2>
    <form method="post" action="{{ route('users.store') }}" class="tiles" style="align-items: end">
      @csrf
      <label>Nama <input name="name" value="{{ old('name') }}" required></label>
      <label>Email <input type="email" name="email" value="{{ old('email') }}" required></label>
      <label>Password (min. 8) <input type="password" name="password" required autocomplete="new-password"></label>
      <label>Role
        <select name="role">@foreach ($roles as $key => $label)<option value="{{ $key }}" @selected(old('role', 'petugas') === $key)>{{ $label }}</option>@endforeach</select>
      </label>
      <button class="btn">Tambah</button>
    </form>
    <p class="note">Admin (bos): lihat dashboard + kelola akun. Petugas: hanya lihat dashboard.</p>
  </section>

  <section class="card" style="overflow-x: auto">
    <h2>Daftar akun</h2>
    <table>
      <thead><tr><th>Nama</th><th>Email</th><th>Role / password baru</th><th></th></tr></thead>
      <tbody>
      @foreach ($users as $user)
        <tr>
          <td>{{ $user->name }}</td>
          <td>{{ $user->email }}</td>
          <td>
            <form method="post" action="{{ route('users.update', $user) }}" style="display: flex; gap: 6px; flex-wrap: wrap">
              @csrf @method('put')
              <select name="role">@foreach ($roles as $key => $label)<option value="{{ $key }}" @selected($user->role === $key)>{{ $label }}</option>@endforeach</select>
              <input type="password" name="password" placeholder="kosongkan jika tetap" autocomplete="new-password">
              <button class="btn small">Simpan</button>
            </form>
          </td>
          <td>
            @unless ($user->is(auth()->user()))
              <form method="post" action="{{ route('users.destroy', $user) }}" onsubmit="return confirm('Hapus akun {{ $user->email }}?')">
                @csrf @method('delete')<button class="btn small danger">Hapus</button>
              </form>
            @endunless
          </td>
        </tr>
      @endforeach
      </tbody>
    </table>
  </section>
</main>
@endsection
