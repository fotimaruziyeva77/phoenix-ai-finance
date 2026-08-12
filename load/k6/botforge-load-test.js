/**
 * BotForge AI — k6 load test (public widget, auth, CRM leads, optional knowledge upload).
 *
 * Run (from this directory):
 *   k6 run botforge-load-test.js
 * Smoke without AI chat:
 *   k6 run --exclude-scenario widget_chat --exclude-scenario rate_limit_probe botforge-load-test.js
 *
 * Env: see env.example. __ENV is read at init.
 */
import http from "k6/http";
import exec from "k6/execution";
import { check, sleep } from "k6";
import { Counter, Rate } from "k6/metrics";

// 429 is expected under probes and per-IP widget limits; still track via http_429_total.
http.setResponseCallback(http.expectedStatuses(429, { min: 200, max: 399 }));

const http429 = new Counter("http_429_total");
const http5xx = new Counter("http_5xx_total");
const checkPass = new Rate("checks_passed");

const BASE = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const WIDGET_KEY = __ENV.PUBLIC_WIDGET_KEY || "";
const WIDGET_ORIGIN = __ENV.WIDGET_ORIGIN || "http://localhost:3000";
const LOGIN_EMAIL = __ENV.LOADTEST_LOGIN_EMAIL || "";
const LOGIN_PASSWORD = __ENV.LOADTEST_LOGIN_PASSWORD || "";
const BOT_ID = __ENV.LOADTEST_BOT_ID || "";
const PDF_PATH = __ENV.LOADTEST_PDF_PATH || "";
const PROFILE = (__ENV.THRESHOLD_PROFILE || "smoke").toLowerCase();

const vuAuthToken = {};

function trackStatus(res) {
  if (res.status === 429) {
    http429.add(1);
  }
  if (res.status >= 500 && res.status < 600) {
    http5xx.add(1);
  }
}

function widgetHeaders() {
  return {
    Origin: WIDGET_ORIGIN,
    Referer: `${WIDGET_ORIGIN}/`,
  };
}

function runCheck(ok) {
  checkPass.add(ok);
  return ok;
}

export function healthCheck() {
  const res = http.get(`${BASE}/api/v1/health`, {
    tags: { endpoint: "health" },
  });
  trackStatus(res);
  runCheck(
    check(res, {
      "health 200": (r) => r.status === 200,
    }),
  );
  sleep(0.3);
}

export function widgetBootstrap() {
  if (!WIDGET_KEY) {
    sleep(0.5);
    return;
  }
  const res = http.get(
    `${BASE}/api/v1/public/widget/${encodeURIComponent(WIDGET_KEY)}/bootstrap`,
    {
      headers: widgetHeaders(),
      tags: { endpoint: "widget_bootstrap" },
    },
  );
  trackStatus(res);
  runCheck(
    check(res, {
      "bootstrap 2xx": (r) => r.status >= 200 && r.status < 300,
    }),
  );
  sleep(0.2 + Math.random() * 0.5);
}

export function widgetChat() {
  if (!WIDGET_KEY) {
    sleep(1);
    return;
  }
  const payload = JSON.stringify({
    message: `Load test vu=${exec.vu.idInTest} iter=${exec.scenario.iterationInInstance}`,
  });
  const res = http.post(
    `${BASE}/api/v1/public/widget/${encodeURIComponent(WIDGET_KEY)}/chat`,
    payload,
    {
      headers: {
        ...widgetHeaders(),
        "Content-Type": "application/json",
      },
      tags: { endpoint: "widget_chat" },
      timeout: "120s",
    },
  );
  trackStatus(res);
  runCheck(
    check(res, {
      "chat 200": (r) => r.status === 200,
      "chat has assistant_text": (r) => {
        if (r.status !== 200) return true;
        try {
          const j = r.json();
          return typeof j.assistant_text === "string" && j.assistant_text.length > 0;
        } catch {
          return false;
        }
      },
    }),
  );
  sleep(5 + Math.random() * 4);
}

export function authLogin() {
  if (!LOGIN_EMAIL || !LOGIN_PASSWORD) {
    sleep(0.5);
    return;
  }
  const body = JSON.stringify({
    email: LOGIN_EMAIL,
    password: LOGIN_PASSWORD,
  });
  const res = http.post(`${BASE}/api/v1/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
    tags: { endpoint: "auth_login" },
  });
  trackStatus(res);
  runCheck(
    check(res, {
      "login 200": (r) => r.status === 200,
      "login has access_token": (r) => {
        if (r.status !== 200) return false;
        try {
          const j = r.json();
          return Boolean(j && j.access_token);
        } catch {
          return false;
        }
      },
    }),
  );
  sleep(0.5 + Math.random());
}

function tokenForVu() {
  const id = exec.vu.idInTest;
  if (vuAuthToken[id]) {
    return vuAuthToken[id];
  }
  if (!LOGIN_EMAIL || !LOGIN_PASSWORD) {
    return "";
  }
  const body = JSON.stringify({
    email: LOGIN_EMAIL,
    password: LOGIN_PASSWORD,
  });
  const res = http.post(`${BASE}/api/v1/auth/login`, body, {
    headers: { "Content-Type": "application/json" },
    tags: { endpoint: "auth_login_warmup" },
  });
  trackStatus(res);
  if (res.status !== 200) {
    return "";
  }
  try {
    const j = res.json();
    vuAuthToken[id] = j.access_token || "";
  } catch {
    vuAuthToken[id] = "";
  }
  return vuAuthToken[id];
}

export function leadsList() {
  if (!LOGIN_EMAIL) {
    sleep(0.5);
    return;
  }
  const token = tokenForVu();
  if (!token) {
    sleep(0.5);
    return;
  }
  const res = http.get(`${BASE}/api/v1/leads?limit=25&offset=0`, {
    headers: { Authorization: `Bearer ${token}` },
    tags: { endpoint: "leads_list" },
  });
  trackStatus(res);
  runCheck(
    check(res, {
      "leads 200": (r) => r.status === 200,
    }),
  );
  sleep(0.3 + Math.random() * 0.7);
}

export function rateLimitProbe() {
  if (!WIDGET_KEY) {
    sleep(0.5);
    return;
  }
  for (let i = 0; i < 25; i++) {
    const res = http.get(
      `${BASE}/api/v1/public/widget/${encodeURIComponent(WIDGET_KEY)}/bootstrap`,
      {
        headers: widgetHeaders(),
        tags: { endpoint: "widget_bootstrap_probe" },
      },
    );
    trackStatus(res);
    if (res.status === 429) {
      break;
    }
  }
  // Interpretation: compare http_429_total vs limits (bootstrap/min per IP). No assert — limits may be off in dev.
}

export function knowledgeUpload() {
  if (!BOT_ID || !PDF_PATH) {
    sleep(0.2);
    return;
  }
  const token = tokenForVu();
  if (!token) {
    sleep(0.2);
    return;
  }
  let bin;
  try {
    bin = open(PDF_PATH, "b");
  } catch {
    sleep(0.2);
    return;
  }
  const res = http.post(
    `${BASE}/api/v1/bots/${BOT_ID}/knowledge/files`,
    { file: http.file(bin, "loadtest.pdf", "application/pdf") },
    {
      headers: { Authorization: `Bearer ${token}` },
      tags: { endpoint: "knowledge_upload" },
      timeout: "120s",
    },
  );
  trackStatus(res);
  runCheck(
    check(res, {
      "upload 201 or 429": (r) => r.status === 201 || r.status === 429,
    }),
  );
  sleep(2);
}

function thresholdsForProfile() {
  const common = {
    checks: ["rate>0.90"],
    checks_passed: ["rate>0.90"],
    http_5xx_total: ["count<50"],
  };
  const smoke = {
    ...common,
    "http_req_duration{endpoint:health}": ["p(95)<800", "p(99)<1500"],
    "http_req_duration{endpoint:widget_bootstrap}": ["p(95)<3000", "p(99)<5000"],
    "http_req_duration{endpoint:auth_login}": ["p(95)<4000", "p(99)<8000"],
    "http_req_duration{endpoint:leads_list}": ["p(95)<3000", "p(99)<6000"],
    "http_req_duration{endpoint:widget_chat}": ["p(95)<90000", "p(99)<120000"],
    http_req_failed: ["rate<0.05"],
  };
  const standard = {
    ...common,
    checks: ["rate>0.95"],
    checks_passed: ["rate>0.95"],
    "http_req_duration{endpoint:health}": ["p(95)<400", "p(99)<800"],
    "http_req_duration{endpoint:widget_bootstrap}": ["p(95)<1500", "p(99)<2500"],
    "http_req_duration{endpoint:auth_login}": ["p(95)<2000", "p(99)<4000"],
    "http_req_duration{endpoint:leads_list}": ["p(95)<1500", "p(99)<3000"],
    "http_req_duration{endpoint:widget_chat}": ["p(95)<60000", "p(99)<90000"],
    http_req_failed: ["rate<0.02"],
  };
  const stress = {
    ...common,
    checks: ["rate>0.85"],
    checks_passed: ["rate>0.85"],
    "http_req_duration{endpoint:health}": ["p(95)<600", "p(99)<1200"],
    "http_req_duration{endpoint:widget_bootstrap}": ["p(95)<2000", "p(99)<4000"],
    "http_req_duration{endpoint:auth_login}": ["p(95)<2500", "p(99)<5000"],
    "http_req_duration{endpoint:leads_list}": ["p(95)<2000", "p(99)<4000"],
    "http_req_duration{endpoint:widget_chat}": ["p(95)<75000", "p(99)<110000"],
    http_req_failed: ["rate<0.03"],
  };
  if (PROFILE === "standard") return standard;
  if (PROFILE === "stress") return stress;
  return smoke;
}

function buildScenarios() {
  const s = {
    health_check: {
      executor: "constant-vus",
      vus: 3,
      duration: "45s",
      startTime: "0s",
      gracefulStop: "5s",
      exec: "healthCheck",
    },
    widget_bootstrap: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "20s", target: 8 },
        { duration: "1m", target: 20 },
        { duration: "45s", target: 20 },
        { duration: "20s", target: 0 },
      ],
      startTime: "5s",
      gracefulStop: "15s",
      exec: "widgetBootstrap",
    },
    auth_login: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "15s", target: 5 },
        { duration: "1m", target: 15 },
        { duration: "30s", target: 15 },
        { duration: "15s", target: 0 },
      ],
      startTime: "10s",
      gracefulStop: "10s",
      exec: "authLogin",
    },
    leads_list: {
      executor: "constant-vus",
      vus: 8,
      duration: "1m30s",
      startTime: "20s",
      gracefulStop: "10s",
      exec: "leadsList",
    },
    widget_chat: {
      executor: "constant-vus",
      vus: 4,
      duration: "2m30s",
      startTime: "25s",
      gracefulStop: "30s",
      exec: "widgetChat",
    },
    rate_limit_probe: {
      executor: "shared-iterations",
      vus: 12,
      iterations: 120,
      maxDuration: "45s",
      startTime: "3m15s",
      gracefulStop: "5s",
      exec: "rateLimitProbe",
    },
  };

  if (BOT_ID && PDF_PATH) {
    s.knowledge_upload = {
      executor: "constant-vus",
      vus: 2,
      duration: "1m",
      startTime: "45s",
      gracefulStop: "20s",
      exec: "knowledgeUpload",
    };
  }

  return s;
}

export const options = {
  scenarios: buildScenarios(),
  thresholds: thresholdsForProfile(),
};
