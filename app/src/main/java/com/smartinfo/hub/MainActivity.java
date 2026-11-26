package com.smartinfo.hub;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class MainActivity extends AppCompatActivity {

    public static final String DATA_URL =
            "https://raw.githubusercontent.com/harshvardhan88945-boop/smart-info-hub/main/data.json";
    public static final String CACHE_FILENAME = "cached_data.json";
    public static final String CHANNEL_ID = "smart_info_channel";
    public static final String PREFS_NAME = "smart_info_prefs";

    public static final String CAT_ALL = "All";
    public static final String CAT_CASE_LAW = "New Case Law and Recent Judgement";
    public static final String CAT_CURRENT_AFFAIRS = "Daily Current Affair";
    public static final String CAT_JOB_VACANCY = "Job and Vacancy";
    public static final String CAT_INTERNSHIP = "Internship";
    public static final String CAT_HISTORY = "History Articles";
    public static final String CAT_SCIENCE_ARCHAEOLOGY = "Science and New Research (Include Archaeology Research)";
    public static final String CAT_PARLIAMENT = "Parliament Update and Activities";
    public static final String CAT_UP_VIDHAN = "UP Vidhan Sabha, Vidhan Parishad News and Activities";
    public static final String CAT_ECONOMICS_COMMERCE = "Economics and Commerce Article";

    private static final List<String> FIXED_CATEGORIES = Arrays.asList(
            CAT_ALL,
            CAT_CASE_LAW,
            CAT_CURRENT_AFFAIRS,
            CAT_JOB_VACANCY,
            CAT_INTERNSHIP,
            CAT_HISTORY,
            CAT_SCIENCE_ARCHAEOLOGY,
            CAT_PARLIAMENT,
            CAT_UP_VIDHAN,
            CAT_ECONOMICS_COMMERCE
    );

    private TextView tvStatus, tvQualificationLabel, tvStateLabel;
    private Spinner spinnerCategory, spinnerQualification, spinnerState;
    private ListView listItems;
    private Button btnRefresh;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final List<FeedItem> allItems = new ArrayList<>();
    private final List<FeedItem> visibleItems = new ArrayList<>();
    private final List<String> categoryOptions = new ArrayList<>();
    private ArrayAdapter<String> categoryAdapter;
    private ArrayAdapter<String> listAdapter;

    private String selectedCategory = CAT_ALL;
    private String selectedQualification = "All";
    private String selectedState = "All";

    static class FeedItem {
        final String id;
        final String kind;
        final String category;
        final String title;
        final String source;
        final String url;
        final String date;
        final List<String> qualifications;
        final String state;

        FeedItem(String id, String kind, String category, String title, String source,
                 String url, String date, List<String> qualifications, String state) {
            this.id = id;
            this.kind = kind;
            this.category = category;
            this.title = title;
            this.source = source;
            this.url = url;
            this.date = date;
            this.qualifications = qualifications;
            this.state = state;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvStatus = findViewById(R.id.tvStatus);
        spinnerCategory = findViewById(R.id.spinnerCategory);
        spinnerQualification = findViewById(R.id.spinnerQualification);
        spinnerState = findViewById(R.id.spinnerState);
        listItems = findViewById(R.id.listItems);
        btnRefresh = findViewById(R.id.btnRefresh);

        int qualLabelId = getResources().getIdentifier("tvQualification", "id", getPackageName());
        int stateLabelId = getResources().getIdentifier("tvState", "id", getPackageName());
        if (qualLabelId != 0) tvQualificationLabel = findViewById(qualLabelId);
        if (stateLabelId != 0) tvStateLabel = findViewById(stateLabelId);

        createNotificationChannel();
        requestNotificationPermissionIfNeeded();
        setupSpinners();
        updateCategorySpinner();
        updateFilterVisibility();
        setupList();
        scheduleBackgroundCheck();

        String cached = readCache();
        if (cached != null && !cached.isEmpty()) {
            parseAndRender(cached, false);
        }

        btnRefresh.setOnClickListener(v -> fetchRemoteData(true));
        listItems.setOnItemClickListener((parent, view, position, id) -> {
            if (position >= 0 && position < visibleItems.size()) {
                String targetUrl = visibleItems.get(position).url;
                if (targetUrl != null && !targetUrl.trim().isEmpty()) {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(targetUrl.trim())));
                } else {
                    openSearchForItem(visibleItems.get(position));
                }
            }
        });

        fetchRemoteData(false);
    }

    public void openSearchForCurrentCategory() {
        String query = selectedCategory;
        if (CAT_ALL.equals(query) || query == null || query.trim().isEmpty()) {
            query = "latest government job notification legal update india";
        } else if (isCareerFilterApplicable()) {
            if (!"All".equals(selectedState)) {
                query += " " + selectedState;
            }
            if (!"All".equals(selectedQualification)) {
                query += " " + selectedQualification;
            }
        }
        openWebSearch(query);
    }

    private void openSearchForItem(FeedItem item) {
        String q = (item.title != null && !item.title.trim().isEmpty())
                ? item.title.trim()
                : item.category;
        openWebSearch(q);
    }

    private void openWebSearch(String query) {
        try {
            String encoded = URLEncoder.encode(query, StandardCharsets.UTF_8.toString());
            Uri uri = Uri.parse("https://www.google.com/search?q=" + encoded);
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (Exception e) {
            Toast.makeText(this, "Search open failed", Toast.LENGTH_SHORT).show();
        }
    }

    private boolean isCareerFilterApplicable() {
        return CAT_JOB_VACANCY.equals(selectedCategory) || CAT_INTERNSHIP.equals(selectedCategory);
    }

    private boolean isCareerItem(FeedItem item) {
        String k = item.kind == null ? "" : item.kind.toLowerCase(Locale.ROOT);
        return "job".equals(k) || "internship".equals(k)
                || CAT_JOB_VACANCY.equalsIgnoreCase(item.category)
                || CAT_INTERNSHIP.equalsIgnoreCase(item.category);
    }

    private void updateFilterVisibility() {
        boolean showFilters = isCareerFilterApplicable();
        int visibility = showFilters ? View.VISIBLE : View.GONE;

        if (!showFilters) {
            selectedQualification = "All";
            selectedState = "All";
            if (spinnerQualification != null && spinnerQualification.getCount() > 0) {
                spinnerQualification.setSelection(0, false);
            }
            if (spinnerState != null && spinnerState.getCount() > 0) {
                spinnerState.setSelection(0, false);
            }
        }

        if (tvQualificationLabel != null) tvQualificationLabel.setVisibility(visibility);
        if (spinnerQualification != null) spinnerQualification.setVisibility(visibility);
        if (tvStateLabel != null) tvStateLabel.setVisibility(visibility);
        if (spinnerState != null) spinnerState.setVisibility(visibility);
    }

    private void setupSpinners() {
        categoryOptions.clear();
        categoryOptions.addAll(FIXED_CATEGORIES);
        categoryAdapter = new ArrayAdapter<>(
                this, android.R.layout.simple_spinner_dropdown_item, categoryOptions);
        spinnerCategory.setAdapter(categoryAdapter);

        spinnerCategory.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int pos, long id) {
                if (pos >= 0 && pos < categoryOptions.size()) {
                    selectedCategory = categoryOptions.get(pos);
                    updateFilterVisibility();
                    applyFilters();
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });

        String[] quals = {"All", "LLB", "Graduation", "Post Graduation", "General"};
        ArrayAdapter<String> qualAdapter = new ArrayAdapter<>(
                this, android.R.layout.simple_spinner_dropdown_item, quals);
        spinnerQualification.setAdapter(qualAdapter);

        String[] states = {"All", "Uttar Pradesh", "All India", "Other / Unspecified"};
        ArrayAdapter<String> stateAdapter = new ArrayAdapter<>(
                this, android.R.layout.simple_spinner_dropdown_item, states);
        spinnerState.setAdapter(stateAdapter);

        spinnerQualification.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int pos, long id) {
                selectedQualification = quals[pos];
                applyFilters();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });

        spinnerState.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int pos, long id) {
                selectedState = states[pos];
                applyFilters();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
            }
        });
    }

    private void updateCategorySpinner() {
        if (categoryAdapter == null) return;

        Set<String> cats = new LinkedHashSet<>(FIXED_CATEGORIES);
        for (FeedItem item : allItems) {
            if (item.category != null && !item.category.trim().isEmpty()) {
                cats.add(item.category.trim());
            }
        }

        categoryOptions.clear();
        categoryOptions.addAll(cats);
        categoryAdapter.notifyDataSetChanged();

        int savedIndex = categoryOptions.indexOf(selectedCategory);
        if (savedIndex >= 0) {
            spinnerCategory.setSelection(savedIndex, false);
        } else {
            selectedCategory = CAT_ALL;
            spinnerCategory.setSelection(0, false);
        }
    }

    private void setupList() {
        listAdapter = new ArrayAdapter<>(
                this, android.R.layout.simple_list_item_2, android.R.id.text1, new ArrayList<>()) {
            @Override
            public View getView(int position, View convertView, android.view.ViewGroup parent) {
                View view = super.getView(position, convertView, parent);
                TextView t1 = view.findViewById(android.R.id.text1);
                TextView t2 = view.findViewById(android.R.id.text2);
                FeedItem item = visibleItems.get(position);

                String safeTitle = (item.title == null || item.title.trim().isEmpty())
                        ? "(No Title)" : item.title.trim();
                t1.setText(safeTitle);

                String safeCat = (item.category == null || item.category.trim().isEmpty())
                        ? "General" : item.category.trim();
                String meta = safeCat + " | " + item.source + " | " + item.date;
                if (isCareerItem(item)) {
                    String qualText = item.qualifications.isEmpty()
                            ? "General" : String.join(", ", item.qualifications);
                    meta += " | Qual: " + qualText + " | " + item.state;
                }
                t2.setText(meta);
                return view;
            }
        };
        listItems.setAdapter(listAdapter);
    }

    private void fetchRemoteData(boolean showToast) {
        tvStatus.setText("Syncing latest data...");
        executor.execute(() -> {
            HttpURLConnection conn = null;
            try {
                URL url = new URL(DATA_URL);
                conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(15000);
                conn.setRequestMethod("GET");

                int code = conn.getResponseCode();
                if (code == HttpURLConnection.HTTP_OK) {
                    BufferedReader reader = new BufferedReader(
                            new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        sb.append(line);
                    }
                    reader.close();
                    String jsonStr = sb.toString();
                    writeCache(jsonStr);

                    runOnUiThread(() -> {
                        parseAndRender(jsonStr, true);
                        if (showToast) {
                            Toast.makeText(this, "Updated", Toast.LENGTH_SHORT).show();
                        }
                    });
                } else {
                    runOnUiThread(() -> tvStatus.setText("HTTP Error: " + code));
                }
            } catch (Exception e) {
                runOnUiThread(() -> tvStatus.setText("Offline / Sync failed: " + e.getMessage()));
            } finally {
                if (conn != null) {
                    conn.disconnect();
                }
            }
        });
    }

    private void parseAndRender(String jsonStr, boolean notifyNewItems) {
        try {
            JSONObject root = new JSONObject(jsonStr);
            String lastUpdated = root.optString("last_updated", "");
            JSONArray articlesArr = root.optJSONArray("articles");
            JSONArray jobsArr = root.optJSONArray("jobs");

            allItems.clear();

            if (jobsArr != null) {
                for (int i = 0; i < jobsArr.length(); i++) {
                    JSONObject obj = jobsArr.getJSONObject(i);
                    List<String> quals = new ArrayList<>();
                    JSONArray qArr = obj.optJSONArray("qualifications");
                    if (qArr != null) {
                        for (int q = 0; q < qArr.length(); q++) {
                            quals.add(qArr.optString(q));
                        }
                    }
                    allItems.add(new FeedItem(
                            obj.optString("id", ""),
                            obj.optString("kind", "job"),
                            obj.optString("category", CAT_JOB_VACANCY),
                            obj.optString("title", ""),
                            obj.optString("source", ""),
                            obj.optString("url", ""),
                            obj.optString("date", ""),
                            quals,
                            obj.optString("state", "Other / Unspecified")
                    ));
                }
            }

            if (articlesArr != null) {
                for (int i = 0; i < articlesArr.length(); i++) {
                    JSONObject obj = articlesArr.getJSONObject(i);
                    allItems.add(new FeedItem(
                            obj.optString("id", ""),
                            obj.optString("kind", "article"),
                            obj.optString("category", "Articles"),
                            obj.optString("title", ""),
                            obj.optString("source", ""),
                            obj.optString("url", ""),
                            obj.optString("date", ""),
                            new ArrayList<>(),
                            "All India"
                    ));
                }
            }

            tvStatus.setText("Total Items: " + allItems.size() + " | Last Updated: " + lastUpdated);
            updateCategorySpinner();
            updateFilterVisibility();
            applyFilters();

            if (notifyNewItems) {
                checkAndNotifyNewItems();
            }
        } catch (Exception e) {
            tvStatus.setText("JSON Parse Error: " + e.getMessage());
        }
    }

    private void applyFilters() {
        visibleItems.clear();
        List<String> labels = new ArrayList<>();
        boolean applyCareerFilters = isCareerFilterApplicable();

        for (FeedItem item : allItems) {
            String itemCat = item.category == null ? "" : item.category.trim();
            boolean catMatch = CAT_ALL.equals(selectedCategory)
                    || selectedCategory.equalsIgnoreCase(itemCat);

            boolean qualMatch = !applyCareerFilters
                    || "All".equals(selectedQualification)
                    || !isCareerItem(item)
                    || item.qualifications.contains(selectedQualification);

            boolean stateMatch = !applyCareerFilters
                    || "All".equals(selectedState)
                    || !isCareerItem(item)
                    || selectedState.equalsIgnoreCase(item.state);

            if (catMatch && qualMatch && stateMatch) {
                visibleItems.add(item);
                String safeTitle = (item.title == null || item.title.trim().isEmpty())
                        ? "(No Title)" : item.title.trim();
                labels.add(safeTitle);
            }
        }

        if (listAdapter != null) {
            listAdapter.clear();
            listAdapter.addAll(labels);
            listAdapter.notifyDataSetChanged();
        }
    }

    private void checkAndNotifyNewItems() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        Set<String> seenIds = new LinkedHashSet<>(prefs.getStringSet("seen_ids", new LinkedHashSet<>()));
        boolean firstRun = seenIds.isEmpty();

        int newCount = 0;
        String latestTitle = "";

        for (FeedItem item : allItems) {
            if (!item.id.isEmpty() && !seenIds.contains(item.id)) {
                seenIds.add(item.id);
                if (!firstRun) {
                    newCount++;
                    latestTitle = item.title;
                }
            }
        }

        prefs.edit().putStringSet("seen_ids", seenIds).apply();

        if (!firstRun && newCount > 0) {
            showPopupNotification(
                    newCount + " New Update(s) Available",
                    latestTitle
            );
        }
    }

    private void showPopupNotification(String title, String body) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                return;
            }
        }

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(body)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true);

        NotificationManagerCompat.from(this).notify((int) System.currentTimeMillis(), builder.build());
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Smart Info Hub Alerts",
                    NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Notifications for new jobs, legal updates, and current affairs");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private void requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(
                        this, new String[]{Manifest.permission.POST_NOTIFICATIONS}, 101);
            }
        }
    }

    private void scheduleBackgroundCheck() {
        try {
            PeriodicWorkRequest workRequest = new PeriodicWorkRequest.Builder(
                    SyncWorker.class, 3, TimeUnit.HOURS
            ).build();

            WorkManager.getInstance(this).enqueueUniquePeriodicWork(
                    "SmartInfoSyncWork",
                    ExistingPeriodicWorkPolicy.KEEP,
                    workRequest
            );
        } catch (Exception ignored) {
        }
    }

    private void writeCache(String content) {
        try {
            FileOutputStream fos = openFileOutput(CACHE_FILENAME, MODE_PRIVATE);
            fos.write(content.getBytes(StandardCharsets.UTF_8));
            fos.close();
        } catch (Exception ignored) {
        }
    }

    private String readCache() {
        try {
            File file = new File(getFilesDir(), CACHE_FILENAME);
            if (!file.exists()) return "";
            FileInputStream fis = openFileInput(CACHE_FILENAME);
            BufferedReader br = new BufferedReader(new InputStreamReader(fis));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line);
            }
            br.close();
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }
}
