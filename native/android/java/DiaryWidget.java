package com.bharattech.businessdiary;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.widget.RemoteViews;

import org.json.JSONArray;

import java.util.Random;

/**
 * Home-screen widget that shows a random empowering quote / bucket-list line.
 * Tapping it shows a new one. Data + on/off flag come from the app via
 * Capacitor Preferences (SharedPreferences "CapacitorStorage").
 */
public class DiaryWidget extends AppWidgetProvider {

    private static final String ACTION_NEXT = "com.bharattech.businessdiary.WIDGET_NEXT";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        for (int id : ids) render(context, manager, id);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_NEXT.equals(intent.getAction())) {
            AppWidgetManager manager = AppWidgetManager.getInstance(context);
            int id = intent.getIntExtra(
                AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID);
            if (id != AppWidgetManager.INVALID_APPWIDGET_ID) {
                render(context, manager, id);
            } else {
                ComponentName cn = new ComponentName(context, DiaryWidget.class);
                for (int wid : manager.getAppWidgetIds(cn)) render(context, manager, wid);
            }
        }
    }

    private String pref(SharedPreferences p, String key, String fallback) {
        String v = p.getString(key, null);
        if (v == null) v = p.getString("_cap_" + key, null); // legacy prefix safety
        return v == null ? fallback : v;
    }

    private void render(Context context, AppWidgetManager manager, int id) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_dev);

        SharedPreferences prefs =
            context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);

        boolean enabled = !"false".equals(pref(prefs, "widgetEnabled", "true"));
        String line;

        if (!enabled) {
            line = "Widget is off. Turn it on in Settings.";
        } else {
            line = "Open Business Diary to add your quotes & goals.";
            try {
                JSONArray arr = new JSONArray(pref(prefs, "widgetLines", "[]"));
                if (arr.length() > 0) {
                    line = arr.getString(new Random().nextInt(arr.length()));
                }
            } catch (Exception ignored) {
            }
        }

        views.setTextViewText(R.id.widget_text, line);

        Intent intent = new Intent(context, DiaryWidget.class);
        intent.setAction(ACTION_NEXT);
        intent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, id);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        PendingIntent pi = PendingIntent.getBroadcast(context, id, intent, flags);
        views.setOnClickPendingIntent(R.id.widget_root, pi);

        manager.updateAppWidget(id, views);
    }
}
