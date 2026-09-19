package com.ruanxiaomi.reader;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

public final class IconRotationWorker extends Worker {
    public IconRotationWorker(@NonNull Context appContext, @NonNull WorkerParameters workerParams) {
        super(appContext, workerParams);
    }

    @NonNull
    @Override
    public Result doWork() {
        DailyIconManager.applyForToday(getApplicationContext());
        return Result.success();
    }
}
