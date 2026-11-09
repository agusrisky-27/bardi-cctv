<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use RuntimeException;

class DatabaseSeeder extends Seeder
{
    /**
     * First admin account from .env (ADMIN_NAME / ADMIN_EMAIL / ADMIN_PASSWORD). Other accounts are made in the web.
     */
    public function run(): void
    {
        $email = env('ADMIN_EMAIL');
        $password = env('ADMIN_PASSWORD');
        if (! $email || ! $password) {
            throw new RuntimeException('Isi ADMIN_EMAIL dan ADMIN_PASSWORD di .env dulu.');
        }

        User::updateOrCreate(
            ['email' => $email],
            ['name' => env('ADMIN_NAME', 'Admin'), 'password' => $password, 'role' => 'admin'],
        );
    }
}
