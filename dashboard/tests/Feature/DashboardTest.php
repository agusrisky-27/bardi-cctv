<?php

namespace Tests\Feature;

use App\Models\User;
use App\Services\StatsService;
use Carbon\CarbonImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

class DashboardTest extends TestCase
{
    use RefreshDatabase;

    private function visit(string $in, string $out, ?string $gender = null, string $role = 'customer', string $side = 'kiri'): void
    {
        DB::table('visits')->insert([
            'track_id' => 1, 'entered_at' => $in, 'exited_at' => $out, 'entry_side' => $side, 'gender_est' => $gender,
            'total_seconds' => CarbonImmutable::parse($out)->diffInSeconds(CarbonImmutable::parse($in), true), 'role' => $role,
        ]);
    }

    public function test_guest_is_sent_to_login_and_cannot_read_stats(): void
    {
        $this->get('/')->assertRedirect('/login');
        $this->getJson('/stats')->assertUnauthorized();
    }

    public function test_login_with_wrong_password_fails(): void
    {
        User::factory()->create(['email' => 'bos@kantor.test', 'password' => 'rahasia123']);
        $this->post('/login', ['email' => 'bos@kantor.test', 'password' => 'salah'])->assertSessionHasErrors('email');
        $this->assertGuest();
    }

    public function test_petugas_sees_dashboard_but_not_user_management(): void
    {
        $petugas = User::factory()->create(['role' => 'petugas']);
        $this->actingAs($petugas)->get('/')->assertOk()->assertSee('Live CCTV');
        $this->actingAs($petugas)->get('/users')->assertForbidden();
    }

    public function test_admin_creates_and_deletes_accounts_but_not_itself(): void
    {
        $admin = User::factory()->create(['role' => 'admin']);
        $this->actingAs($admin)->post('/users', [
            'name' => 'Petugas 1', 'email' => 'p1@kantor.test', 'password' => 'password123', 'role' => 'petugas',
        ])->assertSessionHasNoErrors();
        $p1 = User::where('email', 'p1@kantor.test')->firstOrFail();
        $this->assertSame('petugas', $p1->role);
        $this->actingAs($admin)->delete("/users/{$p1->id}")->assertRedirect();
        $this->assertModelMissing($p1);
        $this->actingAs($admin)->delete("/users/{$admin->id}")->assertStatus(422);
    }

    public function test_stats_count_visits_peak_gender_and_laptop(): void
    {
        $now = CarbonImmutable::parse('2026-11-09 15:00:00');
        $this->visit('2026-11-09 08:00:00', '2026-11-09 09:00:00', 'male');
        $this->visit('2026-11-09 08:30:00', '2026-11-09 08:40:00', 'female', side: 'depan');
        $this->visit('2026-11-09 10:00:00', '2026-11-09 11:00:00', 'male'); // same person back: new visit
        $this->visit('2026-11-09 08:00:00', '2026-11-09 12:00:00', role: 'staff'); // never counted
        $this->visit('2026-11-08 10:00:00', '2026-11-08 10:05:00');
        DB::table('activity_events')->insert([
            ['track_id' => 7, 'activity' => 'laptop', 'start_at' => '2026-11-09 08:05:00', 'end_at' => '2026-11-09 08:15:00', 'seconds' => 600],
            ['track_id' => 7, 'activity' => 'laptop', 'start_at' => '2026-11-09 08:20:00', 'end_at' => '2026-11-09 08:25:00', 'seconds' => 300],
        ]);
        DB::table('zone_events')->insert([
            'track_id' => 1, 'zone_name' => 'sisi_kiri', 'enter_at' => '2026-11-09 08:00:00', 'exit_at' => '2026-11-09 08:30:00', 'seconds' => 1800,
        ]);

        $s = app(StatsService::class)->stats('today', $now);

        $this->assertSame(3, $s['visitors']);
        $this->assertSame(2, $s['peak_people']); // 08:30-08:40 two people at once
        $this->assertSame(['male' => 2, 'female' => 1, 'unknown' => 0], $s['gender']);
        $this->assertSame(2, $s['series']['values'][8]);
        $this->assertSame(['kiri' => 2, 'depan' => 1], $s['entry_sides']->all());
        $this->assertEqualsWithDelta(900.0, $s['laptop']['total_seconds'], 0.01);
        $this->assertSame(2, $s['laptop']['per_person'][0]['sessions']);
        $this->assertSame('sisi_kiri', $s['zones'][0]['zone']);
        $this->assertSame(1, app(StatsService::class)->stats('yesterday', $now)['visitors']);
        $this->assertSame(4, app(StatsService::class)->stats('7d', $now)['visitors']);
    }

    public function test_live_is_unavailable_when_engine_is_stale(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user)->getJson('/live')->assertJson(['available' => false]);
        DB::table('live_status')->insert(['id' => 1, 'people_now' => 3, 'laptop_now' => 1, 'updated_at' => now()]);
        $this->actingAs($user)->getJson('/live')->assertJson(['available' => true, 'people_now' => 3]);
        DB::table('live_status')->update(['updated_at' => now()->subMinutes(5)]);
        $this->actingAs($user)->getJson('/live')->assertJson(['available' => false]);
    }

    public function test_seeder_needs_admin_credentials_from_env(): void
    {
        $env = ['ADMIN_EMAIL' => 'bos@kantor.test', 'ADMIN_PASSWORD' => 'rahasia123'];
        $old = array_map(fn ($k) => $_SERVER[$k] ?? null, array_keys($env));
        foreach ($env as $k => $v) {
            $_SERVER[$k] = $_ENV[$k] = $v; // .env may hold empty values that win over putenv
        }
        try {
            $this->seed();
        } finally {
            foreach (array_keys($env) as $i => $k) {
                $_SERVER[$k] = $_ENV[$k] = $old[$i];
            }
        }
        $this->assertTrue(User::where('email', 'bos@kantor.test')->firstOrFail()->isAdmin());
    }
}
