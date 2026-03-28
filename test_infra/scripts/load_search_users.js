import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// кастомные метрики
export const latency = new Trend('latency', true, { unit: 'ms' });
export const throughput = new Counter('rpc');
export const errors = new Rate('errors');

// Ascii
const FIRST_EN = ['Al', 'Jo', 'Mi', 'Da', 'An', 'Ma', 'Ch', 'El'];
const LAST_EN  = ['Sm', 'Jo', 'Br', 'Wi', 'Da', 'Mi', 'Mo', 'Ta'];

// транслит
const FIRST_TR = ['Ale', 'Dmi', 'Ser', 'And', 'Iva', 'Nata', 'Ol', 'Vla'];
const LAST_TR  = ['Ivan', 'Pet', 'Sido', 'Kuz', 'Sok', 'Mor', 'Vol', 'Fedo'];

// кириллица
const FIRST_RU = ['Ал', 'Дм', 'Се', 'Ан', 'Ив', 'Ма', 'Ол', 'Вл'];
const LAST_RU  = ['Ив', 'Пе', 'Си', 'Ку', 'Со', 'Мо', 'Во', 'Фе'];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function pickSet() {
  const r = Math.random();
  if (r < 0.33) {
    return [pick(FIRST_EN), pick(LAST_EN)];
  } else if (r < 0.66) {
    return [pick(FIRST_TR), pick(LAST_TR)];
  } else {
    return [pick(FIRST_RU), pick(LAST_RU)];
  }
}

export const options = {
  scenarios: {
    search: {
      executor: 'ramping-arrival-rate',
      startRate: 100,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 2000,
      stages: [
        { target: 500, duration: '30s' },
        { target: 1000, duration: '10m' },
        { target: 0, duration: '30s' },
      ],
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const [first, last] = pickSet();
  const url = `http://app:8000/api/v1/user/search?first_name=${encodeURIComponent(first)}&last_name=${encodeURIComponent(last)}`;
  const res = http.get(url, { responseType: 'none' });
  latency.add(res.timings.duration);
  if (res.status === 200) {
    throughput.add(1);
  }
  const ok = check(res, {
    'status 200': (r) => r.status === 200,
  });
  errors.add(!ok);
}