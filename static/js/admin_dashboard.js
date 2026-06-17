// admin_dashboard.js – loads KPI data, charts and tables via the admin API

document.addEventListener('DOMContentLoaded', async () => {
  try {
    // Load KPI cards
    const statsRes = await fetch('/admin/api/dashboard_stats');
    const stats = await statsRes.json();
    updateKpiCards(stats);

    // Load tables
    await loadTopPerformers();
    await loadStudentsAtRisk();
    await loadTrackStats();

    // Load charts
    await renderCompletionFunnel();
    await renderDaywiseCompletion();
    await renderDifficultyPie();
    await renderVerificationDoughnut();
    await renderDailyActiveLine();
  } catch (e) {
    console.error('Admin dashboard init error:', e);
  }
});

function updateKpiCards(stats) {
  const mapping = {
    total_students: 'total_students',
    active_students: 'active_students',
    total_problems: 'total_problems',
    solved_problems: 'solved_problems',
    pending_verifications: 'pending_verifications',
    total_tracks: 'total_tracks',
    avg_completion: 'avg_completion',
    students_completed_current_track: 'students_completed_current_track',
  };
  Object.entries(mapping).forEach(([key, elId]) => {
    const el = document.getElementById(elId);
    if (el && stats[key] !== undefined) el.textContent = stats[key];
  });
}

async function loadTopPerformers() {
  const res = await fetch('/admin/api/top_students');
  const data = await res.json();
  const tbody = document.querySelector('#topPerformersTable tbody');
  tbody.innerHTML = '';
  data.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.rank}</td><td>${row.name}</td><td>${row.roll_no}</td><td>${row.solved}</td><td>${row.completion_percent}%</td><td>${row.current_day}</td>`;
    tbody.appendChild(tr);
  });
}

async function loadStudentsAtRisk() {
  const res = await fetch('/admin/api/students_at_risk');
  const data = await res.json();
  const tbody = document.querySelector('#atRiskTable tbody');
  tbody.innerHTML = '';
  data.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.name}</td><td>${row.roll_no}</td><td>${row.status}</td>`;
    tbody.appendChild(tr);
  });
}

async function loadTrackStats() {
  const res = await fetch('/admin/api/track_completion');
  const data = await res.json();
  const tbody = document.querySelector('#trackStatsTable tbody');
  tbody.innerHTML = '';
  data.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.track_name}</td><td>${row.enrolled}</td><td>${row.completed}</td><td>${row.completion_rate}%</td>`;
    tbody.appendChild(tr);
  });
}

async function renderCompletionFunnel() {
  const res = await fetch('/admin/api/completion_funnel');
  const data = await res.json();
  const ctx = document.getElementById('completionFunnel').getContext('2d');
  new Chart(ctx, {
    type: 'funnel',
    data: {
      labels: ['Registered', 'Day 1', 'Day 7', 'Day 14', 'Day 21', 'Completed Track'],
      datasets: [{
        data: [data.registered, data.started_day1, data.reached_day7, data.reached_day14, data.reached_day21, data.completed_track],
        backgroundColor: ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc949'],
      }]
    },
    options: {plugins: {legend: {display: false}}}
  });
}

async function renderDaywiseCompletion() {
  const res = await fetch('/admin/api/daywise_completion');
  const data = await res.json();
  const labels = Object.keys(data).map(k => `Day ${k}`);
  const values = Object.values(data);
  const ctx = document.getElementById('daywiseCompletion').getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{label: 'Students Completed', data: values, backgroundColor: '#4e79a7'}]
    },
    options: {responsive: true, scales: {y: {beginAtZero: true}}}
  });
}

async function renderDifficultyPie() {
  const res = await fetch('/admin/api/problem_analytics');
  const data = await res.json();
  const diff = data.difficulty_distribution;
  const labels = Object.keys(diff);
  const values = Object.values(diff);
  const ctx = document.getElementById('difficultyPie').getContext('2d');
  new Chart(ctx, {
    type: 'pie',
    data: {
      labels,
      datasets: [{data: values, backgroundColor: ['#4e79a7', '#f28e2b', '#e15759'] }]
    }
  });
}

async function renderVerificationDoughnut() {
  const stats = await fetch('/admin/api/submission_stats').then(r=>r.json());
  const ctx = document.getElementById('verificationDoughnut').getContext('2d');
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Verified', 'Pending', 'Rejected'],
      datasets: [{data: [stats.verified, stats.pending, stats.rejected], backgroundColor: ['#4e79a7', '#f28e2b', '#e15759'] }]
    }
  });
}

async function renderDailyActiveLine() {
  const res = await fetch('/admin/api/engagement');
  const data = await res.json();
  const labels = Object.keys(data.daily_active);
  const values = Object.values(data.daily_active);
  const ctx = document.getElementById('dailyActiveLine').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{label: 'Daily Active Students', data: values, borderColor: '#4e79a7', fill: false}]
    },
    options: {responsive: true, scales: {y: {beginAtZero: true}}}
  });
}
