<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Illuminate\Validation\Rules\Password;
use Illuminate\View\View;

/** Account management, admin (bos) only. Petugas accounts can only view the dashboard. */
class UserController extends Controller
{
    public function index(): View
    {
        return view('users', ['users' => User::orderBy('name')->get(), 'roles' => User::ROLES]);
    }

    public function store(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'name' => ['required', 'string', 'max:100'],
            'email' => ['required', 'email', 'max:150', 'unique:users,email'],
            'password' => ['required', Password::min(8)],
            'role' => ['required', Rule::in(array_keys(User::ROLES))],
        ]);
        User::create($data);

        return back()->with('status', "Akun {$data['email']} dibuat.");
    }

    public function update(Request $request, User $user): RedirectResponse
    {
        $data = $request->validate([
            'role' => ['required', Rule::in(array_keys(User::ROLES))],
            'password' => ['nullable', Password::min(8)],
        ]);
        abort_if($user->is($request->user()) && $data['role'] !== 'admin', 422, 'Tidak bisa menurunkan role akun sendiri.');
        $user->role = $data['role'];
        if (! empty($data['password'])) {
            $user->password = $data['password'];
        }
        $user->save();

        return back()->with('status', "Akun {$user->email} diperbarui.");
    }

    public function destroy(Request $request, User $user): RedirectResponse
    {
        abort_if($user->is($request->user()), 422, 'Tidak bisa menghapus akun sendiri.');
        $user->delete();

        return back()->with('status', "Akun {$user->email} dihapus.");
    }
}
