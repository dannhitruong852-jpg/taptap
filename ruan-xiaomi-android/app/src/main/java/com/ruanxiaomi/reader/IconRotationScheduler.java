package com.ruanxiaomi.reader;

import android.content.Context;

import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import java.time.Duration;
import java.time.ZonedDateTime;
import java.util.concurrent.TimeUnit;

public final class IconRotationScheduler {
    private static final String UNIQUE_WORK = "ruan_xiaomi_daily_icon_rotation";

    private IconRotationScheduler() {}

    public static void ensureScheduled(Context context) {
        ZonedDateTime now = ZonedDateTime.now();
        ZonedDateTime nextRun = now.toLocalDate()
                .plusDays(1)
                .atStartOfDay(now.getZone())
                .plusMinutes(5);
        long initialDelayMs = Math.max(0L, Duration.between(now, nextRun).toMillis());

        PeriodicWorkRequest request = new PeriodicWorkRequest.Builder(
                IconRotationWorker.class,
                24,
                TimeUnit.HOURS
        )
                .setInitialDelay(initialDelayMs, TimeUnit.MILLISECONDS)
                .build();

        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                UNIQUE_WORK,
                ExistingPeriodicWorkPolicy.UPDATE,
                request
        );
    }
}
