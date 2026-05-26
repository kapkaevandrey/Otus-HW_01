import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://app:8000/api/v1";
const TEST_USERS_COUNT = Number(__ENV.TEST_USERS_COUNT || 120);
const PREWARM_MESSAGES_PER_PAIR = Number(__ENV.PREWARM_MESSAGES_PER_PAIR || 10);

export const dialog_send_latency = new Trend("dialog_send_latency", true, { unit: "ms" });
export const dialog_list_latency = new Trend("dialog_list_latency", true, { unit: "ms" });
export const dialog_send_errors = new Rate("dialog_send_errors");
export const dialog_list_errors = new Rate("dialog_list_errors");
export const dialog_send_throughput = new Counter("dialog_send_rpc");
export const dialog_list_throughput = new Counter("dialog_list_rpc");

export const options = {
  setupTimeout: "10m",
  scenarios: {
    dialog_send: {
      executor: "ramping-arrival-rate",
      exec: "sendDialogMessage",
      startRate: 50,
      timeUnit: "1s",
      preAllocatedVUs: 80,
      maxVUs: 600,
      stages: [
        { target: 250, duration: "2m" },
        { target: 250, duration: "8m" },
        { target: 0, duration: "1m" },
      ],
    },
    dialog_list: {
      executor: "ramping-arrival-rate",
      exec: "listDialogMessages",
      startRate: 30,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [
        { target: 150, duration: "2m" },
        { target: 150, duration: "8m" },
        { target: 0, duration: "1m" },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    dialog_send_errors: ["rate<0.05"],
    dialog_list_errors: ["rate<0.05"],
    dialog_send_latency: ["p(95)<30000", "p(99)<60000"],
    dialog_list_latency: ["p(95)<30000", "p(99)<60000"],
  },
};

function buildRegisterPayload(index) {
  return {
    first_name: `load_${index}`,
    second_name: `dialogs_${index}`,
    birthdate: "1995-01-01",
    biography: "Dialog load testing user",
    city: "Moscow",
    password: "Passw0rd!",
  };
}

function extractAccessToken(loginResponse) {
  if (loginResponse.access_token?.token) {
    return loginResponse.access_token.token;
  }
  if (loginResponse.token) {
    return loginResponse.token;
  }
  return null;
}

function authHeader(token) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function warmupPairs(pairs) {
  for (const pair of pairs) {
    for (let i = 0; i < PREWARM_MESSAGES_PER_PAIR; i += 1) {
      const sender = i % 2 === 0 ? pair.left : pair.right;
      const receiver = i % 2 === 0 ? pair.right : pair.left;
      http.post(
        `${BASE_URL}/dialog/${receiver.id}/send`,
        JSON.stringify({ text: `warmup-${i}` }),
        { headers: authHeader(sender.token), responseType: "none" }
      );
    }
  }
}

export function setup() {
  const users = [];
  const params = { headers: { "Content-Type": "application/json" } };

  for (let i = 0; i < TEST_USERS_COUNT; i += 1) {
    const registerRes = http.post(
      `${BASE_URL}/user/register`,
      JSON.stringify(buildRegisterPayload(i)),
      params
    );
    check(registerRes, { "register status is 200": (r) => r.status === 200 });
    const userId = registerRes.json("user_id");
    if (!userId) {
      throw new Error("Failed to extract user_id after registration");
    }

    const loginRes = http.post(
      `${BASE_URL}/login`,
      JSON.stringify({ id: userId, password: "Passw0rd!" }),
      params
    );
    check(loginRes, { "login status is 200": (r) => r.status === 200 });
    const token = extractAccessToken(loginRes.json());
    if (!token) {
      throw new Error("Failed to extract access token");
    }
    users.push({ id: userId, token });
  }

  const pairs = [];
  for (let i = 0; i + 1 < users.length; i += 2) {
    pairs.push({ left: users[i], right: users[i + 1] });
  }

  warmupPairs(pairs);
  return { pairs };
}

export function sendDialogMessage(data) {
  const pair = pick(data.pairs);
  const sender = Math.random() > 0.5 ? pair.left : pair.right;
  const receiver = sender.id === pair.left.id ? pair.right : pair.left;
  const response = http.post(
    `${BASE_URL}/dialog/${receiver.id}/send`,
    JSON.stringify({ text: `load-message-${__VU}-${__ITER}` }),
    { headers: authHeader(sender.token), responseType: "none" }
  );

  dialog_send_latency.add(response.timings.duration);
  const ok = check(response, { "dialog send status is 200": (r) => r.status === 200 });
  dialog_send_errors.add(!ok);
  if (ok) {
    dialog_send_throughput.add(1);
  }
}

export function listDialogMessages(data) {
  const pair = pick(data.pairs);
  const requester = Math.random() > 0.5 ? pair.left : pair.right;
  const peer = requester.id === pair.left.id ? pair.right : pair.left;
  const response = http.get(`${BASE_URL}/dialog/${peer.id}/list`, {
    headers: authHeader(requester.token),
    responseType: "none",
  });

  dialog_list_latency.add(response.timings.duration);
  const ok = check(response, { "dialog list status is 200": (r) => r.status === 200 });
  dialog_list_errors.add(!ok);
  if (ok) {
    dialog_list_throughput.add(1);
  }
  sleep(0.1);
}
