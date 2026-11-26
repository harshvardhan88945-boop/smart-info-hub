package com.smartinfo.hub;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.LinkedHashSet;
import java.util.Set;

public class SyncWorker extends Worker {

    public SyncWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(MainActivity.DATA_URL);
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);
            conn.setRequestMethod("GET");

            if (conn.getResponseCode() == HttpURLConnection.HTTP_OK) {
                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
                reader.close();
                String jsonStr = sb.toString();

                try (FileOutputStream fos = getApplicationContext()
                        .openFileOutput(MainActivity.CACHE_FILENAME, Context.MODE_PRIVATE)) {
                    fos.write(jsonStr.getBytes("UTF-8"));
                }

                checkNewItemsAndNotify(jsonStr);
            }
            return Result.success();
        } catch (Exception e) {
            return Result.retry();
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    private void checkNewItemsAndNotify(String jsonStr) {
        try {
            JSONObject root = new JSONObject(jsonStr);
            SharedPreferences prefs = getApplicationContext()
                    .getSharedPreferences(MainActivity.PREFS_NAME, Context.MODE_PRIVATE);
            Set<String> seenIds = new LinkedHashSet<>(
                    prefs.getStringSet("seen_ids", new LinkedHashSet<>()));
            boolean firstRun = seenIds.isEmpty();

            int newCount = 0;
            String latestTitle = "";

            String[] arrays = {"jobs", "articles"};
            for (String arrName : arrays) {
                JSONArray arr = root.optJSONArray(arrName);
                if (arr != null) {
                    for (int i = 0; i < arr.length(); i++) {
                        JSONObject obj = arr.getJSONObject(i);
                        String id = obj.optString("id", "");
                        String title = obj.optString("title", "");
                        if (!id.isEmpty() && !seenIds.contains(id)) {
                            seenIds.add(id);
                            if (!firstRun) {
                                newCount++;
                                latestTitle = title;
                            }
                        }
                    }
                }
            }

            prefs.edit().putStringSet("seen_ids", seenIds).apply();

            if (!firstRun && newCount > 0) {
                Context ctx = getApplicationContext();
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    NotificationChannel channel = new NotificationChannel(
                            MainActivity.CHANNEL_ID,
                            "Smart Info Hub Alerts",
                            NotificationManager.IMPORTANCE_HIGH
                    );
                    NotificationManager manager = ctx.getSystemService(NotificationManager.class);
                    if (manager != null) {
                        manager.createNotificationChannel(channel);
                    }
                }

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    if (ActivityCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS)
                            != PackageManager.PERMISSION_GRANTED) {
                        return;
                    }
                }

                NotificationCompat.Builder builder = new NotificationCompat.Builder(
                        ctx, MainActivity.CHANNEL_ID)
                        .setSmallIcon(android.R.drawable.ic_dialog_info)
                        .setContentTitle(newCount + " New Update(s) Available")
                        .setContentText(latestTitle)
                        .setPriority(NotificationCompat.PRIORITY_HIGH)
                        .setAutoCancel(true);

                NotificationManagerCompat.from(ctx)
                        .notify((int) System.currentTimeMillis(), builder.build());
            }
        } catch (Exception ignored) {
        }
    }
}
