package com.ruanxiaomi.reader;

import android.app.Application;

public final class RuanXiaomiApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        DailyIconManager.applyForToday(this);
        IconRotationScheduler.ensureScheduled(this);
    }
}
