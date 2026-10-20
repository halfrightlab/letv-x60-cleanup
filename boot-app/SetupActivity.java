package com.judeyang.x60boot;
import android.app.Activity;
import android.os.Bundle;

public final class SetupActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        Launch.open(this, "SETUP");
        finish();
    }
}
