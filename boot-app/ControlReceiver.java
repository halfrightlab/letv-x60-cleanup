package com.judeyang.x60boot;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import org.json.JSONObject;

public final class ControlReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        try {
            if ("com.judeyang.x60boot.TEST".equals(intent.getAction())) {
                Launch.open(context, "TEST");
            } else if ("com.judeyang.x60boot.TEST_VENDOR".equals(intent.getAction())) {
                Launch.schedule(context, true);
            } else if (!"com.judeyang.x60boot.CHECK".equals(intent.getAction())) {
                throw new IllegalArgumentException("Unknown action");
            }
            SharedPreferences values = context.getSharedPreferences("status", 0);
            JSONObject result = new JSONObject();
            result.put("reason", values.getString("reason", "NEVER"));
            result.put("elapsed_ms", values.getLong("elapsed_ms", -1));
            result.put("boot_elapsed_ms", values.getLong("boot_elapsed_ms", -1));
            result.put("error", values.getString("error", ""));
            result.put("current_boot_id", Launch.bootId());
            result.put("launched_boot_id", values.getString("launched_boot_id", ""));
            setResultCode(0);
            setResultData(result.toString());
        } catch (Exception error) {
            setResultCode(1);
            setResultData(error.toString());
        }
    }
}
