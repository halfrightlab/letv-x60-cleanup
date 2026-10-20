package com.judeyang.x60boot;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Launch.boot(context, "BOOT_COMPLETED");
        } else if ("com.letv.helper.restart.BOOT_COMPLETED".equals(intent.getAction())) {
            Launch.schedule(context, false);
        }
    }
}
