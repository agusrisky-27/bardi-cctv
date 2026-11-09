<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Anonymous analytics written by the Python engine (src/rcis/storage.py).
 * Keep database/rcis.sql and tests/memdb.py (Python tests) in sync with this file.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('visits', function (Blueprint $table) {
            $table->id();
            $table->integer('track_id');
            $table->dateTime('entered_at')->index();
            $table->dateTime('exited_at')->nullable();
            $table->string('entry_side', 20)->nullable();
            $table->string('gender_est', 10)->nullable();
            $table->double('gender_conf')->nullable();
            $table->double('total_seconds')->nullable();
            $table->string('role', 20)->default('customer');
        });
        Schema::create('zone_events', function (Blueprint $table) {
            $table->id();
            $table->integer('track_id');
            $table->string('zone_name', 100)->index();
            $table->dateTime('enter_at')->index();
            $table->dateTime('exit_at')->nullable();
            $table->double('seconds')->nullable();
            $table->boolean('is_sitting')->default(false);
        });
        Schema::create('table_sessions', function (Blueprint $table) {
            $table->id();
            $table->string('table_zone', 100);
            $table->dateTime('seated_at')->index();
            $table->dateTime('food_arrived_at')->nullable();
            $table->double('wait_seconds')->nullable();
            $table->dateTime('left_at')->nullable();
        });
        Schema::create('alerts', function (Blueprint $table) {
            $table->id();
            $table->string('type', 50);
            $table->string('zone_name', 100)->nullable();
            $table->dateTime('created_at')->index();
            $table->string('snapshot_path_blurred')->nullable();
        });
        Schema::create('line_crossings', function (Blueprint $table) {
            $table->id();
            $table->integer('track_id');
            $table->string('direction', 5);
            $table->string('entry_side', 20)->nullable();
            $table->dateTime('crossed_at')->index();
        });
        Schema::create('activity_events', function (Blueprint $table) {
            $table->id();
            $table->integer('track_id');
            $table->string('activity', 30);
            $table->dateTime('start_at')->index();
            $table->dateTime('end_at');
            $table->double('seconds');
        });
        Schema::create('live_status', function (Blueprint $table) {
            $table->unsignedTinyInteger('id')->primary(); // always 1: current state of the engine
            $table->integer('people_now')->default(0);
            $table->integer('laptop_now')->default(0);
            $table->integer('count_in')->default(0);
            $table->integer('count_out')->default(0);
            $table->double('fps')->nullable();
            $table->dateTime('updated_at');
        });
    }

    public function down(): void
    {
        foreach (['live_status', 'activity_events', 'line_crossings', 'alerts', 'table_sessions', 'zone_events', 'visits'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
