package com.judeyang.x60boot;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.os.Build;
import android.os.SystemClock;
import java.io.BufferedReader;
import java.io.FileReader;

final class Launch {
    static String bootId() throws Exception {
        BufferedReader reader = new BufferedReader(new FileReader("/proc/sys/kernel/random/boot_id"));
        try {
            String value = reader.readLine();
            if (value == null || !value.matches("[0-9a-f-]{36}")) {
                throw new IllegalStateException("Boot identity unavailable");
            }
            return value;
        } finally {
            reader.close();
        }
    }

    static void boot(Context context, String reason) {
        try {
            String epoch = bootId();
            SharedPreferences status = context.getSharedPreferences("status", 0);
            if (epoch.equals(status.getString("launched_boot_id", ""))) return;
            if (open(context, reason)) status.edit().putString("launched_boot_id", epoch).commit();
        } catch (Exception error) {
            context.getSharedPreferences("status", 0).edit().putString("error", error.toString()).commit();
        }
    }

    static void schedule(Context context, boolean test) {
        try {
            String epoch = bootId();
            SharedPreferences status = context.getSharedPreferences("status", 0);
            if (!test && (epoch.equals(status.getString("launched_boot_id", ""))
                    || epoch.equals(status.getString("pending_boot_id", "")))) return;
            Intent next = new Intent(context, DeferredReceiver.class);
            next.putExtra("test", test);
            PendingIntent pending = PendingIntent.getBroadcast(context, test ? 1 : 0,
                    next, PendingIntent.FLAG_UPDATE_CURRENT);
            AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            alarms.set(AlarmManager.ELAPSED_REALTIME, SystemClock.elapsedRealtime() + 2000, pending);
            SharedPreferences.Editor editor = status.edit().putString("error", "");
            if (!test) editor.putString("pending_boot_id", epoch);
            editor.commit();
        } catch (Exception error) {
            context.getSharedPreferences("status", 0).edit().putString("error", error.toString()).commit();
        }
    }

    static boolean open(Context context, String reason) {
        SharedPreferences.Editor status = context.getSharedPreferences("status", 0).edit();
        status.putString("reason", reason).putLong("elapsed_ms", SystemClock.elapsedRealtime());
        if ("BOOT_COMPLETED".equals(reason) || "VENDOR_BOOT".equals(reason)) {
            status.putLong("boot_elapsed_ms", SystemClock.elapsedRealtime());
        }
        try {
            if (!"LeTVX60".equals(Build.MODEL)
                    || !Build.DISPLAY.contains("V1101RCN02C060070B07031S")) {
                throw new IllegalStateException("Unsupported device");
            }
            Intent launch = new Intent(Intent.ACTION_MAIN);
            launch.addCategory(Intent.CATEGORY_HOME);
            launch.setClassName("org.cosinus.launchertv", "org.cosinus.launchertv.Launcher");
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            context.startActivity(launch);
            status.putString("error", "");
            status.commit();
            return true;
        } catch (RuntimeException error) {
            status.putString("error", error.toString());
        }
        status.commit();
        return false;
    }
}
