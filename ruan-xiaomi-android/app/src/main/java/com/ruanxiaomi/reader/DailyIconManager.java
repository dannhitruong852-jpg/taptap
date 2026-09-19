package com.ruanxiaomi.reader;

import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;

import java.time.LocalDate;

public final class DailyIconManager {
    private static final String PREFS = "ruan_xiaomi_icon_cycle";
    private static final String START_EPOCH_DAY = "start_epoch_day";

    private static final String[] ALIASES = {
            "com.ruanxiaomi.reader.IconDay1",
            "com.ruanxiaomi.reader.IconDay2",
            "com.ruanxiaomi.reader.IconDay3",
            "com.ruanxiaomi.reader.IconDay4",
            "com.ruanxiaomi.reader.IconDay5"
    };

    private DailyIconManager() {}

    public static int applyForToday(Context context) {
        long today = LocalDate.now().toEpochDay();
        SharedPreferences preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        long start = preferences.getLong(START_EPOCH_DAY, Long.MIN_VALUE);
        if (start == Long.MIN_VALUE) {
            start = today;
            preferences.edit().putLong(START_EPOCH_DAY, start).apply();
        }

        int desiredIndex = Math.floorMod((int) (today - start), ALIASES.length);
        PackageManager packageManager = context.getPackageManager();

        ComponentName desired = new ComponentName(context, ALIASES[desiredIndex]);
        packageManager.setComponentEnabledSetting(
                desired,
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                PackageManager.DONT_KILL_APP
        );

        for (int i = 0; i < ALIASES.length; i++) {
            if (i == desiredIndex) continue;
            ComponentName component = new ComponentName(context, ALIASES[i]);
            packageManager.setComponentEnabledSetting(
                    component,
                    PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                    PackageManager.DONT_KILL_APP
            );
        }

        return desiredIndex + 1;
    }
}
