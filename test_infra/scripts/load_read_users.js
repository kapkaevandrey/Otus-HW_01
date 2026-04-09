import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// кастомные метрики
export const search_latency = new Trend('search_latency', true, { unit: 'ms' });
export const search_throughput = new Counter('search_rpc');
export const search_errors = new Rate('search_errors');

export const get_user_latency = new Trend('get_user_latency', true, { unit: 'ms' });
export const get_user_throughput = new Counter('get_user_rpc');
export const get_user_errors = new Rate('get_user_errors');


const USER_IDS = new SharedArray('ids', () =>
  JSON.parse(open('./user_ids.json'))
);

const SEARCH_PAIRS = new SharedArray('pairs', () =>
  JSON.parse(open('./search_pairs.json'))
);

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function pickSearch() {
  return SEARCH_PAIRS[Math.floor(Math.random() * SEARCH_PAIRS.length)];
}

export const options = {
  scenarios: {
    search: {
      executor: 'ramping-arrival-rate',
      exec: 'searchUser',
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 500,
      stages: [
        { target: 200, duration: '2m' },
        { target: 200, duration: '10m' },
        { target: 0, duration: '1m' },
      ],
    },

    get_user: {
      executor: 'ramping-arrival-rate',
      exec: 'getUser',
      startRate: 100, // обычно чтение чаще
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 1500,
      stages: [
        { target: 800, duration: '2m' },
        { target: 800, duration: '10m' },
        { target: 0, duration: '30s' },
      ],
    },
  },

  thresholds: {
    http_req_failed: ['rate<0.01'],

    'search_latency': ['p(95)<700', 'p(99)<1200'],
    'search_errors': ['rate<0.02'],

    'get_user_latency': ['p(95)<200', 'p(99)<400'],
    'get_user_errors': ['rate<0.01'],
  },
};

export function searchUser () {
  const { first, last } = pickSearch();
  const url = `http://app:8000/api/v1/user/search?first_name=${encodeURIComponent(first)}&last_name=${encodeURIComponent(last)}`;
  const res = http.get(url, { responseType: 'none' });
  search_latency.add(res.timings.duration);
  if (res.status === 200) {
    search_throughput.add(1);
  }
  const ok = check(res, {
    'status 200': (r) => r.status === 200,
  });
  search_errors.add(!ok);
}

export function getUser () {
  const id = pick(USER_IDS);
  const url = `http://app:8000/api/v1/user/get/${id}`;
  const res = http.get(url, { responseType: 'none' });
  get_user_latency.add(res.timings.duration);
  if (res.status === 200) {
    get_user_throughput.add(1);
  }
  const ok = check(res, {
    'status 200': (r) => r.status === 200,
  });
  get_user_errors.add(!ok);
}