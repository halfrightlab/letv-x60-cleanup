package com.judeyang.x60boot;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class DeferredReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (intent.getBooleanExtra("test", false)) {
            Launch.open(context, "TEST_VENDOR_BOOT");
        } else {
            Launch.boot(context, "VENDOR_BOOT");
        }
    }
}
